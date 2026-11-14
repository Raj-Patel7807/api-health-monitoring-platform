"""Unit tests for B5 alert dispatch (US-11).

Tests:
1. pick_channels returns monitor-specific channels when they exist.
2. pick_channels falls back to team-wide when no monitor-specific channels.
3. pick_channels skips disabled channels.
4. pick_channels skips soft-deleted channels.
5. create_delivery_rows creates one row per channel.
6. create_delivery_rows is idempotent (no duplicates on second call).
7. send_alert_task skips already-sent deliveries.
8. SlackSender calls the webhook URL with correct payload (mocked httpx).
9. DiscordSender calls the webhook URL with correct payload (mocked httpx).
10. A failed Slack send sets status=failed, attempt_count=1, sanitized error_message.
11. A failed channel does not block other channels.
12. Secret is never logged or stored in error_message.
13. get_sender raises ValueError for unknown channel type.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.crypto import encrypt, generate_key
from app.db.base import Base
from app.modules.alerts.models import AlertDelivery, DeliveryEventType, DeliveryStatus
from app.modules.alerts.senders import (
    AlertMessage,
    DiscordSender,
    SlackSender,
    get_sender,
)
from app.modules.channels.models import NotificationChannel
from app.modules.incidents.models import Incident
from app.modules.monitors.models import Monitor

# ---------------------------------------------------------------------------
# Test encryption key setup
# ---------------------------------------------------------------------------
_TEST_KEY = generate_key()


@pytest.fixture(autouse=True)
def _patch_encryption_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config as cfg

    cfg.get_settings.cache_clear()
    monkeypatch.setenv("ENCRYPTION_KEY", _TEST_KEY)


# ---------------------------------------------------------------------------
# Shared SQLite in-memory engine / session factory
# ---------------------------------------------------------------------------

_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
)


# Allow SQLite to use UUID as text
@event.listens_for(_ENGINE, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):  # type: ignore[misc]
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


_SESSION_FACTORY = sessionmaker(bind=_ENGINE, autocommit=False, autoflush=False)


@pytest.fixture(scope="module", autouse=True)
def _create_tables():
    """Create all tables in-memory once for the module."""
    # We need to register all models before create_all
    # Import models to register them with Base
    from app.modules.alerts.models import AlertDelivery  # noqa: F401
    from app.modules.channels.models import NotificationChannel  # noqa: F401
    from app.modules.incidents.models import Incident  # noqa: F401
    from app.modules.monitors.models import Monitor  # noqa: F401
    from app.modules.results.models import HealthCheckResult  # noqa: F401

    # SQLite doesn't support postgres-specific enum DDL — use String for enum columns
    # We patch by creating tables with metadata that SQLAlchemy generates for SQLite
    Base.metadata.create_all(_ENGINE)
    yield
    Base.metadata.drop_all(_ENGINE)


@pytest.fixture
def session():
    """Return a fresh session, rolling back after each test."""
    s = _SESSION_FACTORY()
    try:
        yield s
        s.rollback()
    finally:
        s.close()


# ---------------------------------------------------------------------------
# Helpers to create test objects
# ---------------------------------------------------------------------------


def _make_team_id() -> uuid.UUID:
    return uuid.uuid4()


def _make_monitor(session: Session, team_id: uuid.UUID) -> Monitor:
    m = Monitor(
        id=uuid.uuid4(),
        team_id=team_id,
        name="Test Monitor",
        url="https://api.example.com",
        method="GET",
        enabled=True,
        check_interval_seconds=60,
        current_interval_seconds=60,
        timeout_seconds=10,
        failure_threshold=3,
        recovery_threshold=2,
        consecutive_failures=0,
        consecutive_successes=0,
        expected_status_code=200,
    )
    session.add(m)
    session.flush()
    return m


def _make_incident(session: Session, monitor: Monitor) -> Incident:
    inc = Incident(
        id=uuid.uuid4(),
        monitor_id=monitor.id,
        status="open",
        opened_at=datetime.now(UTC),
        failure_count=1,
        recovery_count=0,
    )
    session.add(inc)
    session.flush()
    return inc


def _make_channel(
    session: Session,
    team_id: uuid.UUID,
    monitor_id: uuid.UUID | None = None,
    is_enabled: bool = True,
    deleted: bool = False,
    channel_type: str = "slack",
    secret_ref: str = "encrypted_secret",
) -> NotificationChannel:
    ch = NotificationChannel(
        id=uuid.uuid4(),
        team_id=team_id,
        monitor_id=monitor_id,
        type=channel_type,
        name=f"Channel-{uuid.uuid4().hex[:6]}",
        is_enabled=is_enabled,
        configuration="{}",
        secret_ref=secret_ref,
        deleted_at=datetime.now(UTC) if deleted else None,
    )
    session.add(ch)
    session.flush()
    return ch


# ---------------------------------------------------------------------------
# 1. pick_channels: returns monitor-specific channels when they exist
# ---------------------------------------------------------------------------


def test_pick_channels_returns_monitor_specific(session: Session) -> None:
    from app.modules.alerts.dispatcher import pick_channels

    team_id = _make_team_id()
    monitor = _make_monitor(session, team_id)

    # Monitor-specific channel
    mon_ch = _make_channel(session, team_id, monitor_id=monitor.id)
    # Team-wide channel (should be ignored)
    _make_channel(session, team_id, monitor_id=None)

    result = pick_channels(session, monitor.id, team_id)
    ids = [c.id for c in result]
    assert mon_ch.id in ids
    # Team-wide should NOT be returned when monitor-specific exists
    assert len(result) == 1


# ---------------------------------------------------------------------------
# 2. pick_channels: falls back to team-wide when no monitor-specific
# ---------------------------------------------------------------------------


def test_pick_channels_falls_back_to_team_wide(session: Session) -> None:
    from app.modules.alerts.dispatcher import pick_channels

    team_id = _make_team_id()
    monitor = _make_monitor(session, team_id)

    # Only team-wide channel
    team_ch = _make_channel(session, team_id, monitor_id=None)

    result = pick_channels(session, monitor.id, team_id)
    assert len(result) == 1
    assert result[0].id == team_ch.id


# ---------------------------------------------------------------------------
# 3. pick_channels: skips disabled channels
# ---------------------------------------------------------------------------


def test_pick_channels_skips_disabled(session: Session) -> None:
    from app.modules.alerts.dispatcher import pick_channels

    team_id = _make_team_id()
    monitor = _make_monitor(session, team_id)

    _make_channel(session, team_id, monitor_id=monitor.id, is_enabled=False)

    result = pick_channels(session, monitor.id, team_id)
    assert result == []


# ---------------------------------------------------------------------------
# 4. pick_channels: skips soft-deleted channels
# ---------------------------------------------------------------------------


def test_pick_channels_skips_soft_deleted(session: Session) -> None:
    from app.modules.alerts.dispatcher import pick_channels

    team_id = _make_team_id()
    monitor = _make_monitor(session, team_id)

    _make_channel(session, team_id, monitor_id=monitor.id, deleted=True)

    result = pick_channels(session, monitor.id, team_id)
    assert result == []


# ---------------------------------------------------------------------------
# 5. create_delivery_rows: creates one row per channel
# ---------------------------------------------------------------------------


def test_create_delivery_rows_creates_rows(session: Session) -> None:
    from app.modules.alerts.dispatcher import create_delivery_rows

    team_id = _make_team_id()
    monitor = _make_monitor(session, team_id)
    incident = _make_incident(session, monitor)
    ch1 = _make_channel(session, team_id)
    ch2 = _make_channel(session, team_id, channel_type="discord")

    deliveries = create_delivery_rows(session, incident.id, [ch1, ch2], "opened")
    assert len(deliveries) == 2
    statuses = {d.status for d in deliveries}
    assert statuses == {DeliveryStatus.PENDING}


# ---------------------------------------------------------------------------
# 6. create_delivery_rows: idempotent (no duplicate rows on second call)
# ---------------------------------------------------------------------------


def test_create_delivery_rows_is_idempotent(session: Session) -> None:
    from app.modules.alerts.dispatcher import create_delivery_rows

    team_id = _make_team_id()
    monitor = _make_monitor(session, team_id)
    incident = _make_incident(session, monitor)
    ch = _make_channel(session, team_id)

    d1 = create_delivery_rows(session, incident.id, [ch], "opened")
    d2 = create_delivery_rows(session, incident.id, [ch], "opened")

    assert len(d1) == 1
    assert len(d2) == 1
    assert d1[0].id == d2[0].id


# ---------------------------------------------------------------------------
# 7. send_alert_task: skips already-sent deliveries (idempotency)
# ---------------------------------------------------------------------------


def test_send_alert_task_skips_already_sent(session: Session) -> None:
    team_id = _make_team_id()
    monitor = _make_monitor(session, team_id)
    incident = _make_incident(session, monitor)
    ch = _make_channel(session, team_id)

    delivery = AlertDelivery(
        id=uuid.uuid4(),
        incident_id=incident.id,
        notification_channel_id=ch.id,
        event_type=DeliveryEventType.OPENED,
        status=DeliveryStatus.SENT,
        attempt_count=1,
        sent_at=datetime.now(UTC),
    )
    session.add(delivery)
    session.commit()

    # Patch get_db_session to use our test session
    from collections.abc import Generator
    from contextlib import contextmanager

    @contextmanager
    def _mock_session() -> Generator[Session, None, None]:
        yield session

    from app.workers import tasks as tasks_module

    with patch.object(tasks_module, "get_db_session", _mock_session):
        from app.workers.tasks import send_alert_task

        result = send_alert_task.run(str(delivery.id))

    assert result == str(delivery.id)
    # Status must still be SENT (not changed)
    session.refresh(delivery)
    assert delivery.status == DeliveryStatus.SENT


# ---------------------------------------------------------------------------
# 8. SlackSender: calls webhook with correct payload
# ---------------------------------------------------------------------------


def test_slack_sender_posts_correct_payload() -> None:
    secret_url = "https://hooks.slack.com/services/ABC/DEF/GHI"
    encrypted = encrypt(secret_url)

    channel = MagicMock()
    channel.secret_ref = encrypted

    message = AlertMessage(
        monitor_name="Test API",
        monitor_url="https://api.example.com",
        event_type="opened",
        checked_at=datetime(2026, 11, 13, 10, 0, 0, tzinfo=UTC),
        failure_reason="Expected status 200, got 500",
    )

    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None

    with patch("httpx.Client") as mock_client_cls:
        mock_client = mock_client_cls.return_value.__enter__.return_value
        mock_client.post.return_value = mock_response

        SlackSender().send(channel, message)

        call_args = mock_client.post.call_args
        url_called = call_args[0][0]
        payload = call_args[1]["json"]

    assert url_called == secret_url
    assert "text" in payload
    assert "[OPENED]" in payload["text"]
    assert "Test API" in payload["text"]
    assert "Expected status 200, got 500" in payload["text"]


# ---------------------------------------------------------------------------
# 9. DiscordSender: calls webhook with correct payload
# ---------------------------------------------------------------------------


def test_discord_sender_posts_correct_payload() -> None:
    from app.core.crypto import encrypt

    secret_url = "https://discord.com/api/webhooks/123/TOKEN"
    encrypted = encrypt(secret_url)

    channel = MagicMock()
    channel.secret_ref = encrypted

    message = AlertMessage(
        monitor_name="Prod API",
        monitor_url="https://prod.example.com",
        event_type="resolved",
        checked_at=datetime(2026, 11, 13, 11, 0, 0, tzinfo=UTC),
        failure_reason=None,
    )

    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None

    with patch("httpx.Client") as mock_client_cls:
        mock_client = mock_client_cls.return_value.__enter__.return_value
        mock_client.post.return_value = mock_response

        DiscordSender().send(channel, message)

        call_args = mock_client.post.call_args
        url_called = call_args[0][0]
        payload = call_args[1]["json"]

    assert url_called == secret_url
    assert "content" in payload
    assert "[RESOLVED]" in payload["content"]
    assert "Prod API" in payload["content"]


# ---------------------------------------------------------------------------
# 10. Failed Slack send sets status=failed, attempt_count=1, sanitized error_message
# ---------------------------------------------------------------------------


def test_send_alert_task_on_slack_failure(session: Session) -> None:
    from app.core.crypto import encrypt

    team_id = _make_team_id()
    monitor = _make_monitor(session, team_id)
    incident = _make_incident(session, monitor)

    secret_url = "https://hooks.slack.com/services/FAIL/FAIL/FAIL"
    encrypted = encrypt(secret_url)
    ch = _make_channel(session, team_id, channel_type="slack", secret_ref=encrypted)

    delivery = AlertDelivery(
        id=uuid.uuid4(),
        incident_id=incident.id,
        notification_channel_id=ch.id,
        event_type=DeliveryEventType.OPENED,
        status=DeliveryStatus.PENDING,
        attempt_count=0,
    )
    session.add(delivery)
    session.commit()

    from collections.abc import Generator
    from contextlib import contextmanager

    @contextmanager
    def _mock_session() -> Generator[Session, None, None]:
        yield session

    import httpx

    tasks_module = __import__("app.workers.tasks", fromlist=["get_db_session"])
    with (
        patch.object(tasks_module, "get_db_session", _mock_session),
        patch("httpx.Client") as mock_client_cls,
    ):
        mock_client = mock_client_cls.return_value.__enter__.return_value
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server error", request=MagicMock(), response=mock_response
        )
        mock_client.post.return_value = mock_response

        from app.workers.tasks import send_alert_task

        send_alert_task.run(str(delivery.id))

    session.refresh(delivery)
    assert delivery.status == DeliveryStatus.FAILED
    assert delivery.attempt_count == 1
    assert delivery.error_message is not None
    # Secret URL must NOT appear in error_message
    assert secret_url not in (delivery.error_message or "")


# ---------------------------------------------------------------------------
# 11. A failed channel does not block other channels
# ---------------------------------------------------------------------------


def test_failed_channel_does_not_block_others(session: Session) -> None:
    from app.core.crypto import encrypt
    from app.modules.alerts.dispatcher import create_delivery_rows

    team_id = _make_team_id()
    monitor = _make_monitor(session, team_id)
    incident = _make_incident(session, monitor)

    failing_url = "https://hooks.slack.com/services/FAIL/FAIL/FAIL"
    good_url = "https://discord.com/api/webhooks/999/GOOD"
    ch_fail = _make_channel(session, team_id, channel_type="slack", secret_ref=encrypt(failing_url))
    ch_good = _make_channel(session, team_id, channel_type="discord", secret_ref=encrypt(good_url))

    deliveries = create_delivery_rows(session, incident.id, [ch_fail, ch_good], "opened")
    session.commit()

    from collections.abc import Generator
    from contextlib import contextmanager

    @contextmanager
    def _mock_session() -> Generator[Session, None, None]:
        yield session

    import httpx

    call_count = 0

    def _mock_post(url, **kwargs):  # type: ignore[no-untyped-def]
        nonlocal call_count
        call_count += 1
        mock_resp = MagicMock()
        if "FAIL" in url:
            mock_resp.status_code = 500
            mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "fail", request=MagicMock(), response=mock_resp
            )
        else:
            mock_resp.raise_for_status.return_value = None
        return mock_resp

    tasks_module = __import__("app.workers.tasks", fromlist=["get_db_session"])
    with (
        patch.object(tasks_module, "get_db_session", _mock_session),
        patch("httpx.Client") as mock_client_cls,
    ):
        mock_client = mock_client_cls.return_value.__enter__.return_value
        mock_client.post.side_effect = _mock_post

        from app.workers.tasks import send_alert_task

        for d in deliveries:
            send_alert_task.run(str(d.id))

    # Refresh all
    for d in deliveries:
        session.refresh(d)

    statuses = {d.notification_channel_id: d.status for d in deliveries}
    assert statuses[ch_fail.id] == DeliveryStatus.FAILED
    assert statuses[ch_good.id] == DeliveryStatus.SENT


# ---------------------------------------------------------------------------
# 12. Secret is never logged or stored in error_message
# ---------------------------------------------------------------------------


def test_secret_never_in_error_message(session: Session) -> None:
    from app.core.crypto import encrypt

    team_id = _make_team_id()
    monitor = _make_monitor(session, team_id)
    incident = _make_incident(session, monitor)

    secret_url = "https://hooks.slack.com/services/SECRET_TOKEN_HERE"
    ch = _make_channel(session, team_id, channel_type="slack", secret_ref=encrypt(secret_url))

    delivery = AlertDelivery(
        id=uuid.uuid4(),
        incident_id=incident.id,
        notification_channel_id=ch.id,
        event_type=DeliveryEventType.OPENED,
        status=DeliveryStatus.PENDING,
        attempt_count=0,
    )
    session.add(delivery)
    session.commit()

    from collections.abc import Generator
    from contextlib import contextmanager

    @contextmanager
    def _mock_session() -> Generator[Session, None, None]:
        yield session

    import httpx

    tasks_module = __import__("app.workers.tasks", fromlist=["get_db_session"])
    with (
        patch.object(tasks_module, "get_db_session", _mock_session),
        patch("httpx.Client") as mock_client_cls,
    ):
        mock_client = mock_client_cls.return_value.__enter__.return_value
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"403 Forbidden {secret_url}", request=MagicMock(), response=mock_resp
        )
        mock_client.post.return_value = mock_resp

        from app.workers.tasks import send_alert_task

        send_alert_task.run(str(delivery.id))

    session.refresh(delivery)
    assert delivery.status == DeliveryStatus.FAILED
    # The raw secret URL must not appear in error_message
    assert secret_url not in (delivery.error_message or "")
    assert "SECRET_TOKEN_HERE" not in (delivery.error_message or "")


# ---------------------------------------------------------------------------
# 13. get_sender raises ValueError for unknown channel type
# ---------------------------------------------------------------------------


def test_get_sender_raises_for_unknown_type() -> None:
    with pytest.raises(ValueError, match="Unsupported alert channel type"):
        get_sender("telegram")

    with pytest.raises(ValueError):
        get_sender("email")

    # Known types must not raise
    assert isinstance(get_sender("slack"), SlackSender)
    assert isinstance(get_sender("discord"), DiscordSender)

"""Unit tests for exponential backoff, recovery, and User-Agent header (US-16)."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.modules.monitors.backoff import (
    DEFAULT_USER_AGENT,
    MAX_BACKOFF_INTERVAL_SECONDS,
    MIN_BACKOFF_INTERVAL_SECONDS,
    apply_failure_backoff,
    calculate_exponential_backoff,
    reset_monitor_backoff,
    update_monitor_backoff,
)
from app.modules.monitors.checker import (
    check_monitor_by_id,
    execute_http_check,
)
from app.modules.monitors.models import Monitor
from app.modules.monitors.scheduler import find_and_schedule_due_monitors


@pytest.fixture
def in_memory_db() -> Session:
    """Provide a clean in-memory SQLite session for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    yield session
    session.close()


@pytest.fixture
def sample_monitor(in_memory_db: Session) -> Monitor:
    """Create a sample monitor for testing."""
    monitor = Monitor(
        id=uuid4(),
        team_id=uuid4(),
        name="Payments API",
        url="https://api.example.com/health",
        method="GET",
        check_interval_seconds=60,
        current_interval_seconds=60,
        timeout_seconds=10,
        expected_status_code=200,
        user_agent=DEFAULT_USER_AGENT,
        enabled=True,
    )
    in_memory_db.add(monitor)
    in_memory_db.commit()
    in_memory_db.refresh(monitor)
    return monitor


# ===========================================================================
# 1. Pure calculation tests: progression, first failure, overflow, cap
# ===========================================================================


def test_calculate_exponential_backoff_first_failure_doubles_interval() -> None:
    """AC-16.3: A failing monitor is checked less frequently starting from failure 1."""
    base_interval = 60
    assert calculate_exponential_backoff(base_interval, consecutive_failures=1) == 120


def test_calculate_exponential_backoff_progression() -> None:
    """Repeated failures scale exponentially by powers of 2."""
    base = 60
    assert calculate_exponential_backoff(base, consecutive_failures=1) == 120
    assert calculate_exponential_backoff(base, consecutive_failures=2) == 240
    assert calculate_exponential_backoff(base, consecutive_failures=3) == 480
    assert calculate_exponential_backoff(base, consecutive_failures=4) == 960
    assert calculate_exponential_backoff(base, consecutive_failures=5) == 1920


def test_calculate_exponential_backoff_caps_at_maximum_interval() -> None:
    """Interval never exceeds the specified maximum ceiling (default 86400s / 24h)."""
    base = 60
    assert (
        calculate_exponential_backoff(base, consecutive_failures=20) == MAX_BACKOFF_INTERVAL_SECONDS
    )
    assert (
        calculate_exponential_backoff(base, consecutive_failures=50) == MAX_BACKOFF_INTERVAL_SECONDS
    )

    # Custom max cap
    assert (
        calculate_exponential_backoff(base, consecutive_failures=5, max_interval_seconds=500) == 500
    )


def test_calculate_exponential_backoff_zero_or_negative_failures() -> None:
    """Zero or negative failures return the bounded base interval without backoff."""
    base = 60
    assert calculate_exponential_backoff(base, consecutive_failures=0) == 60
    assert calculate_exponential_backoff(base, consecutive_failures=-1) == 60


def test_calculate_exponential_backoff_enforces_minimum_interval() -> None:
    """Calculated intervals always satisfy the DB constraint (>= 10 seconds)."""
    assert (
        calculate_exponential_backoff(base_interval_seconds=5, consecutive_failures=0)
        == MIN_BACKOFF_INTERVAL_SECONDS
    )


# ===========================================================================
# 2. State transition tests: failure backoff, UTC timing, recovery
# ===========================================================================


def test_apply_failure_backoff_sets_interval_and_utc_window(sample_monitor: Monitor) -> None:
    """Applying failure backoff updates current_interval_seconds and backoff_until in UTC."""
    fixed_now = datetime(2026, 10, 14, 12, 0, 0, tzinfo=UTC)
    sample_monitor.consecutive_failures = 2

    new_interval = apply_failure_backoff(sample_monitor, now=fixed_now)

    assert new_interval == 240
    assert sample_monitor.current_interval_seconds == 240
    assert sample_monitor.backoff_until == fixed_now + timedelta(seconds=240)
    assert sample_monitor.backoff_until.tzinfo is not None
    assert sample_monitor.backoff_until.tzinfo == UTC


def test_reset_monitor_backoff_restores_configured_interval(sample_monitor: Monitor) -> None:
    """Recovered monitor restores normal check_interval_seconds and clears backoff_until."""
    sample_monitor.current_interval_seconds = 480
    sample_monitor.backoff_until = datetime.now(UTC) + timedelta(minutes=10)

    reset_monitor_backoff(sample_monitor)

    assert sample_monitor.current_interval_seconds == 60
    assert sample_monitor.backoff_until is None


def test_update_monitor_backoff_delegates_correctly(sample_monitor: Monitor) -> None:
    """update_monitor_backoff applies failure backoff or reset based on is_healthy."""
    fixed_now = datetime(2026, 10, 14, 12, 0, 0, tzinfo=UTC)

    # 1. Failure outcome
    sample_monitor.consecutive_failures = 1
    update_monitor_backoff(sample_monitor, is_healthy=False, now=fixed_now)
    assert sample_monitor.current_interval_seconds == 120
    assert sample_monitor.backoff_until == fixed_now + timedelta(seconds=120)

    # 2. Recovery outcome
    update_monitor_backoff(sample_monitor, is_healthy=True, now=fixed_now)
    assert sample_monitor.current_interval_seconds == 60
    assert sample_monitor.backoff_until is None


# ===========================================================================
# 3. User-Agent Header in Outbound Requests
# ===========================================================================


def test_execute_http_check_transmits_configured_user_agent() -> None:
    """Outbound HTTP requests include the monitor's configured User-Agent header."""
    captured_headers: dict[str, str] = {}

    def fake_request(
        method: str, url: str, headers: dict[str, str] | None = None, **kwargs: object
    ) -> httpx.Response:
        if headers:
            captured_headers.update(headers)
        return httpx.Response(status_code=200, request=httpx.Request("GET", url))

    with patch("httpx.Client.request", side_effect=fake_request):
        execute_http_check(
            url="https://api.example.com",
            method="GET",
            expected_status_code=200,
            timeout_seconds=5,
            user_agent="CustomProbe/2.0",
            monitor_id=str(uuid4()),
        )

    assert captured_headers.get("User-Agent") == "CustomProbe/2.0"


def test_check_monitor_by_id_uses_default_user_agent_when_missing(
    in_memory_db: Session, sample_monitor: Monitor
) -> None:
    """When monitor.user_agent is None or whitespace, fallback to default APIMonitor/1.0."""
    sample_monitor.user_agent = "   "
    in_memory_db.add(sample_monitor)
    in_memory_db.commit()

    captured_headers: dict[str, str] = {}

    def fake_request(
        method: str, url: str, headers: dict[str, str] | None = None, **kwargs: object
    ) -> httpx.Response:
        if headers:
            captured_headers.update(headers)
        return httpx.Response(status_code=200, request=httpx.Request("GET", url))

    with patch("httpx.Client.request", side_effect=fake_request):
        check_monitor_by_id(str(sample_monitor.id), db_session=in_memory_db)

    assert captured_headers.get("User-Agent") == DEFAULT_USER_AGENT


# ===========================================================================
# 4. End-to-end integration: repeated failures, escalation, recovery reset
# ===========================================================================


def test_check_monitor_repeated_failures_and_recovery(
    in_memory_db: Session, sample_monitor: Monitor
) -> None:
    """Simulate consecutive failures causing backoff escalation followed by recovery reset."""
    fixed_time = datetime(2026, 10, 14, 10, 0, 0, tzinfo=UTC)

    # 1. First failure -> current_interval = 120
    with (
        patch(
            "httpx.Client.request",
            return_value=httpx.Response(
                status_code=500, request=httpx.Request("GET", sample_monitor.url)
            ),
        ),
        patch("app.modules.monitors.backoff.datetime") as mock_dt,
    ):
        mock_dt.now.return_value = fixed_time
        mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
        res1 = check_monitor_by_id(str(sample_monitor.id), db_session=in_memory_db)

    assert res1 is not None
    assert res1.status == "failing"
    in_memory_db.refresh(sample_monitor)
    assert sample_monitor.consecutive_failures == 1
    assert sample_monitor.current_interval_seconds == 120
    assert sample_monitor.backoff_until == fixed_time + timedelta(seconds=120)

    # 2. Second failure -> current_interval = 240
    with (
        patch(
            "httpx.Client.request",
            return_value=httpx.Response(
                status_code=500, request=httpx.Request("GET", sample_monitor.url)
            ),
        ),
        patch("app.modules.monitors.backoff.datetime") as mock_dt,
    ):
        mock_dt.now.return_value = fixed_time
        mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
        res2 = check_monitor_by_id(str(sample_monitor.id), db_session=in_memory_db)

    assert res2 is not None
    assert res2.status == "failing"
    in_memory_db.refresh(sample_monitor)
    assert sample_monitor.consecutive_failures == 2
    assert sample_monitor.current_interval_seconds == 240
    assert sample_monitor.backoff_until == fixed_time + timedelta(seconds=240)

    # 3. Third failure -> current_interval = 480
    with (
        patch(
            "httpx.Client.request",
            return_value=httpx.Response(
                status_code=500, request=httpx.Request("GET", sample_monitor.url)
            ),
        ),
        patch("app.modules.monitors.backoff.datetime") as mock_dt,
    ):
        mock_dt.now.return_value = fixed_time
        mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
        res3 = check_monitor_by_id(str(sample_monitor.id), db_session=in_memory_db)

    assert res3 is not None
    assert res3.status == "failing"
    in_memory_db.refresh(sample_monitor)
    assert sample_monitor.consecutive_failures == 3
    assert sample_monitor.current_interval_seconds == 480
    assert sample_monitor.backoff_until == fixed_time + timedelta(seconds=480)

    # 4. Successful recovery check -> resets to check_interval_seconds (60) and clears backoff_until
    with patch(
        "httpx.Client.request",
        return_value=httpx.Response(
            status_code=200, request=httpx.Request("GET", sample_monitor.url)
        ),
    ):
        res_ok = check_monitor_by_id(str(sample_monitor.id), db_session=in_memory_db)

    assert res_ok is not None
    assert res_ok.status == "healthy"
    in_memory_db.refresh(sample_monitor)
    assert sample_monitor.consecutive_failures == 0
    assert sample_monitor.consecutive_successes == 1
    assert sample_monitor.current_interval_seconds == 60
    assert sample_monitor.backoff_until is None


# ===========================================================================
# 5. Scheduler integration with backoff
# ===========================================================================


def test_scheduler_respects_active_backoff_and_schedules_after_expiration(
    in_memory_db: Session, sample_monitor: Monitor
) -> None:
    """Active backoff window prevents scheduling;
    expired backoff schedules with expanded interval.
    """
    now = datetime(2026, 10, 14, 12, 0, 0, tzinfo=UTC)

    # Active backoff: due by next_check_at, but backoff_until is in the future
    sample_monitor.next_check_at = now - timedelta(seconds=10)
    sample_monitor.backoff_until = now + timedelta(seconds=60)
    sample_monitor.current_interval_seconds = 240
    in_memory_db.add(sample_monitor)
    in_memory_db.commit()

    dispatched: list[str] = []
    queued = find_and_schedule_due_monitors(
        session=in_memory_db, now=now, task_dispatcher=dispatched.append
    )

    assert queued == []
    assert dispatched == []

    # Expired backoff window: now eligible for scheduling
    sample_monitor.backoff_until = now - timedelta(seconds=5)
    in_memory_db.add(sample_monitor)
    in_memory_db.commit()

    queued = find_and_schedule_due_monitors(
        session=in_memory_db, now=now, task_dispatcher=dispatched.append
    )

    assert queued == [str(sample_monitor.id)]
    assert dispatched == [str(sample_monitor.id)]

    in_memory_db.refresh(sample_monitor)
    # next_check_at should be advanced using current_interval_seconds (240s)
    assert sample_monitor.next_check_at == now + timedelta(seconds=240)

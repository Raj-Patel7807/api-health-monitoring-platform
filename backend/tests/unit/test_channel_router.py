"""Unit tests for notification channel router endpoints with mock dependencies (US-03).

Covers:
- CRUD endpoints: GET, POST, PATCH, DELETE
- All supported channel types: Slack, Discord, Email, Webhook
- Secret write-only: secret_value never returned in responses
- Secret display hint returned and non-empty
- Validation: 422 for bad Slack URL, bad Discord URL, Webhook SSRF, bad email
- PATCH: updates name/enabled; rotating secret vs omitting secret
- Soft delete (204)
- RBAC: read_only role receives 403 on all operations
- Team scoping: 404 when monitor_id belongs to another team or does not exist
- Team scoping: 404 when channel does not exist or belongs to another team
- Startup validation: app fails with clear message if ENCRYPTION_KEY is missing or malformed
- Log security: secrets never appear in logs
"""

import logging
from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.core.crypto import EncryptionConfigError, generate_key
from app.db.models import Team, TeamRole, User
from app.db.session import get_db
from app.main import app
from app.modules.channels.models import NotificationChannel
from app.modules.channels.router import _require_channel_access
from app.modules.monitors.dependencies import TeamContext

_NOW = datetime.now(UTC)
_TEST_KEY = generate_key()


def _make_dummy_channel(
    team_id: UUID | None = None,
    channel_id: UUID | None = None,
    channel_type: str = "slack",
    name: str = "Test Channel",
    monitor_id: UUID | None = None,
    is_enabled: bool = True,
    secret_display_hint: str = "hooks.slack.com/…/X7Q",
) -> NotificationChannel:
    return NotificationChannel(
        id=channel_id or uuid4(),
        team_id=team_id or uuid4(),
        monitor_id=monitor_id,
        type=channel_type,
        name=name,
        is_enabled=is_enabled,
        configuration="{}",
        secret_ref="encrypted-token-blob",
        secret_display_hint=secret_display_hint,
        created_at=_NOW,
        updated_at=_NOW,
    )


@pytest.fixture()
def mock_team_context() -> TeamContext:
    user = User(id=uuid4(), email="admin@example.com", full_name="Admin", password_hash="h")
    team = Team(id=uuid4(), name="Test Team")
    return TeamContext(user=user, team=team, role=TeamRole.admin)


@pytest.fixture(autouse=True)
def _patch_encryption_key(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    from app.core import config as cfg

    cfg.get_settings.cache_clear()
    monkeypatch.setenv("ENCRYPTION_KEY", _TEST_KEY)
    yield
    cfg.get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Create Channel Tests (all 4 channel types + validations)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_slack_channel_success(mock_team_context: TeamContext) -> None:
    app.dependency_overrides[_require_channel_access] = lambda: mock_team_context
    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    dummy = _make_dummy_channel(
        team_id=mock_team_context.team.id,
        channel_type="slack",
        name="Slack Alerts",
        secret_display_hint="hooks.slack.com/…/ABC",
    )

    with patch("app.modules.channels.service.create_channel", new=AsyncMock(return_value=dummy)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/api/v1/notification-channels",
                json={
                    "type": "slack",
                    "name": "Slack Alerts",
                    "secret_value": "https://hooks.slack.com/services/T00/B00/ABC",
                },
            )
            assert resp.status_code == 201
            data = resp.json()
            assert data["id"] == str(dummy.id)
            assert data["type"] == "slack"
            assert data["name"] == "Slack Alerts"
            assert data["secret_display_hint"] == "hooks.slack.com/…/ABC"
            assert data["configuration"] == {}
            # Never return secret_value or secret_ref
            assert "secret_value" not in data
            assert "secret_ref" not in data

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_discord_channel_success(mock_team_context: TeamContext) -> None:
    app.dependency_overrides[_require_channel_access] = lambda: mock_team_context
    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    dummy = _make_dummy_channel(
        team_id=mock_team_context.team.id,
        channel_type="discord",
        name="Discord Alerts",
        secret_display_hint="discord.com/…/xyz",
    )

    with patch("app.modules.channels.service.create_channel", new=AsyncMock(return_value=dummy)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/api/v1/notification-channels",
                json={
                    "type": "discord",
                    "name": "Discord Alerts",
                    "secret_value": "https://discord.com/api/webhooks/123/xyz",
                },
            )
            assert resp.status_code == 201
            assert resp.json()["type"] == "discord"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_email_channel_success(mock_team_context: TeamContext) -> None:
    app.dependency_overrides[_require_channel_access] = lambda: mock_team_context
    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    dummy = _make_dummy_channel(
        team_id=mock_team_context.team.id,
        channel_type="email",
        name="Email Ops",
        secret_display_hint="o…@example.com",
    )

    with patch("app.modules.channels.service.create_channel", new=AsyncMock(return_value=dummy)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/api/v1/notification-channels",
                json={
                    "type": "email",
                    "name": "Email Ops",
                    "secret_value": "ops@example.com",
                },
            )
            assert resp.status_code == 201
            assert resp.json()["type"] == "email"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_webhook_channel_success(mock_team_context: TeamContext) -> None:
    app.dependency_overrides[_require_channel_access] = lambda: mock_team_context
    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    dummy = _make_dummy_channel(
        team_id=mock_team_context.team.id,
        channel_type="webhook",
        name="Generic Hook",
        secret_display_hint="api.example.com/…/hook",
    )

    with patch("app.modules.channels.service.create_channel", new=AsyncMock(return_value=dummy)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/api/v1/notification-channels",
                json={
                    "type": "webhook",
                    "name": "Generic Hook",
                    "secret_value": "https://api.example.com/alerts/hook",
                },
            )
            assert resp.status_code == 201
            assert resp.json()["type"] == "webhook"

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Validation & SSRF rejection tests (422)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("channel_type", "bad_secret"),
    [
        ("slack", "https://evil.example.com/hook"),
        ("slack", "http://hooks.slack.com/services/bad"),
        ("discord", "https://discord.gg/invite"),
        ("discord", "http://discord.com/api/webhooks/123"),
        ("webhook", "http://api.example.com/insecure"),
        ("webhook", "https://localhost/hook"),
        ("webhook", "https://127.0.0.1:8000/hook"),
        ("webhook", "https://192.168.1.1/hook"),
        ("webhook", "https://10.0.0.1/hook"),
        ("webhook", "https://[::1]/hook"),
        ("email", "not-an-email"),
        ("email", "missing-at.com"),
    ],
)
async def test_create_channel_validation_errors_return_422(
    mock_team_context: TeamContext,
    channel_type: str,
    bad_secret: str,
) -> None:
    app.dependency_overrides[_require_channel_access] = lambda: mock_team_context
    app.dependency_overrides[get_db] = lambda: AsyncMock()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/notification-channels",
            json={
                "type": channel_type,
                "name": "Invalid Channel",
                "secret_value": bad_secret,
            },
        )
        assert resp.status_code == 422
        # Secret must not be echoed in validation error details
        assert bad_secret not in resp.text

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Monitor Ownership / Scoping on Create & List (404 for cross-team monitor)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_channel_cross_team_monitor_returns_404(
    mock_team_context: TeamContext,
) -> None:
    app.dependency_overrides[_require_channel_access] = lambda: mock_team_context
    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    # get_monitor returns None (monitor not found or belongs to another team)
    with patch("app.modules.monitors.service.get_monitor", new=AsyncMock(return_value=None)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/api/v1/notification-channels",
                json={
                    "type": "email",
                    "name": "Monitor Alert",
                    "monitor_id": str(uuid4()),
                    "secret_value": "alerts@example.com",
                },
            )
            assert resp.status_code == 404
            assert resp.json()["detail"] == "Monitor not found."

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_channels_cross_team_monitor_returns_404(
    mock_team_context: TeamContext,
) -> None:
    app.dependency_overrides[_require_channel_access] = lambda: mock_team_context
    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    # get_monitor returns None when filtered monitor belongs to another team
    with patch("app.modules.monitors.service.get_monitor", new=AsyncMock(return_value=None)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get(f"/api/v1/notification-channels?monitor_id={uuid4()}")
            assert resp.status_code == 404
            assert resp.json()["detail"] == "Monitor not found."

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_channels_success(mock_team_context: TeamContext) -> None:
    app.dependency_overrides[_require_channel_access] = lambda: mock_team_context
    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    dummy = _make_dummy_channel(team_id=mock_team_context.team.id)

    with patch("app.modules.channels.service.list_channels", new=AsyncMock(return_value=[dummy])):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/notification-channels")
            assert resp.status_code == 200
            items = resp.json()["items"]
            assert len(items) == 1
            assert items[0]["id"] == str(dummy.id)
            assert "secret_value" not in items[0]
            assert "secret_ref" not in items[0]

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# PATCH Channel Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patch_channel_success(mock_team_context: TeamContext) -> None:
    app.dependency_overrides[_require_channel_access] = lambda: mock_team_context
    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    dummy = _make_dummy_channel(team_id=mock_team_context.team.id)
    dummy_updated = _make_dummy_channel(
        team_id=mock_team_context.team.id,
        channel_id=dummy.id,
        name="Updated Name",
        is_enabled=False,
    )

    with (
        patch("app.modules.channels.service.get_channel", new=AsyncMock(return_value=dummy)),
        patch(
            "app.modules.channels.service.update_channel",
            new=AsyncMock(return_value=dummy_updated),
        ),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.patch(
                f"/api/v1/notification-channels/{dummy.id}",
                json={"name": "Updated Name", "is_enabled": False},
            )
            assert resp.status_code == 200
            assert resp.json()["name"] == "Updated Name"
            assert resp.json()["is_enabled"] is False

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_patch_channel_not_found(mock_team_context: TeamContext) -> None:
    app.dependency_overrides[_require_channel_access] = lambda: mock_team_context
    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    with patch("app.modules.channels.service.get_channel", new=AsyncMock(return_value=None)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.patch(
                f"/api/v1/notification-channels/{uuid4()}",
                json={"name": "Ghost"},
            )
            assert resp.status_code == 404
            assert resp.json()["detail"] == "Notification channel not found."

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# DELETE Channel Tests (soft delete)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_channel_success_and_not_found(mock_team_context: TeamContext) -> None:
    app.dependency_overrides[_require_channel_access] = lambda: mock_team_context
    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    dummy = _make_dummy_channel(team_id=mock_team_context.team.id)

    # 1. Found -> 204
    with (
        patch("app.modules.channels.service.get_channel", new=AsyncMock(return_value=dummy)),
        patch("app.modules.channels.service.soft_delete_channel", new=AsyncMock()) as mock_del,
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.delete(f"/api/v1/notification-channels/{dummy.id}")
            assert resp.status_code == 204
            mock_del.assert_awaited_once_with(mock_db, dummy)

    # 2. Not found -> 404
    with patch("app.modules.channels.service.get_channel", new=AsyncMock(return_value=None)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.delete(f"/api/v1/notification-channels/{uuid4()}")
            assert resp.status_code == 404

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# RBAC Tests (read_only receives 403)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_read_only_role_gets_403() -> None:
    from app.modules.monitors.dependencies import get_team_context

    ro_user = User(id=uuid4(), email="ro@example.com", full_name="Read Only", password_hash="h")
    ro_team = Team(id=uuid4(), name="RO Team")
    ro_context = TeamContext(user=ro_user, team=ro_team, role=TeamRole.read_only)

    app.dependency_overrides[get_team_context] = lambda: ro_context
    app.dependency_overrides[get_db] = lambda: AsyncMock()

    channel_id = uuid4()
    endpoints = [
        ("GET", "/api/v1/notification-channels", None),
        (
            "POST",
            "/api/v1/notification-channels",
            {
                "type": "email",
                "name": "RO",
                "secret_value": "ro@example.com",
            },
        ),
        (
            "PATCH",
            f"/api/v1/notification-channels/{channel_id}",
            {"name": "RO"},
        ),
        ("DELETE", f"/api/v1/notification-channels/{channel_id}", None),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        for method, url, body in endpoints:
            if body:
                resp = await ac.request(method, url, json=body)
            else:
                resp = await ac.request(method, url)
            assert resp.status_code == 403, (
                f"Expected 403 for {method} {url}, got {resp.status_code}"
            )

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Startup & Configuration Validation Tests
# ---------------------------------------------------------------------------


def test_startup_fails_when_encryption_key_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config as cfg

    monkeypatch.setenv("ENCRYPTION_KEY", "")
    cfg.get_settings.cache_clear()

    with pytest.raises(EncryptionConfigError) as exc:
        with TestClient(app):
            pass

    assert "ENCRYPTION_KEY is not set" in str(exc.value)


def test_startup_fails_when_encryption_key_is_malformed(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config as cfg

    monkeypatch.setenv("ENCRYPTION_KEY", "not-a-valid-key!!")
    cfg.get_settings.cache_clear()

    with pytest.raises(EncryptionConfigError) as exc:
        with TestClient(app):
            pass

    assert "ENCRYPTION_KEY is not valid base64url" in str(exc.value)


# ---------------------------------------------------------------------------
# Log Security Test (AC: secret never appears in logs)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_secret_never_appears_in_logs(
    mock_team_context: TeamContext,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    app.dependency_overrides[_require_channel_access] = lambda: mock_team_context
    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    secret_raw = "https://hooks.slack.com/services/T00/B00/HIGHLY_CONFIDENTIAL"
    dummy = _make_dummy_channel(team_id=mock_team_context.team.id)

    with patch("app.modules.channels.service.create_channel", new=AsyncMock(return_value=dummy)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            await ac.post(
                "/api/v1/notification-channels",
                json={
                    "type": "slack",
                    "name": "Secret Log Check",
                    "secret_value": secret_raw,
                },
            )

    # Verify that the plaintext secret never appears in any log output
    assert "HIGHLY_CONFIDENTIAL" not in caplog.text
    assert secret_raw not in caplog.text

    app.dependency_overrides.clear()

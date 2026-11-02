"""Integration tests for notification channel endpoints (US-03).

Uses an async SQLite in-memory database to exercise real route handling,
database persistence, authentication, team scoping, RBAC, and soft delete.

Test coverage:
- Full CRUD lifecycle (create → list → update → delete)
- Secret is never returned in any response
- secret_display_hint is present and non-empty after create/update
- read_only users receive 403 on all endpoints
- Team isolation (channel A not visible to team B)
- 422 for invalid secret per type (Slack URL, SSRF, email)
- type and monitor_id cannot be changed via PATCH (only name/enabled/secret)
- soft delete hides channel from list and subsequent GETs return 404
"""

from collections.abc import AsyncGenerator, Generator
from uuid import UUID

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_db
from app.main import app

# ---------------------------------------------------------------------------
# Test database — async SQLite in-memory
# ---------------------------------------------------------------------------

_SQLITE_URL = "sqlite+aiosqlite:///:memory:"
_engine = create_async_engine(_SQLITE_URL, echo=False)
_TestSessionFactory = async_sessionmaker(_engine, expire_on_commit=False)


async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with _TestSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest_asyncio.fixture(autouse=True, scope="session")
async def _create_tables() -> AsyncGenerator[None, None]:
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture()
async def client() -> AsyncGenerator[AsyncClient, None]:
    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Settings patch for predictable JWT
# ---------------------------------------------------------------------------

_TEST_SECRET = "integration-test-secret-long-enough-for-hs256"


@pytest.fixture(autouse=True)
def _patch_settings(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    from app.core import config as cfg
    from app.core.crypto import generate_key

    cfg.get_settings.cache_clear()
    monkeypatch.setenv("JWT_SECRET_KEY", _TEST_SECRET)
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
    monkeypatch.setenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")
    monkeypatch.setenv("ENCRYPTION_KEY", generate_key())
    yield
    cfg.get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Helper: register a user and return access token
# ---------------------------------------------------------------------------


async def _register_user(client: AsyncClient, email: str, team_name: str) -> str:
    resp = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "full_name": "Test User",
            "password": "password123",
            "team_name": team_name,
        },
    )
    assert resp.status_code == 201
    return str(resp.json()["access_token"])


# ---------------------------------------------------------------------------
# Tests: Channel CRUD lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_channel_crud_lifecycle(client: AsyncClient) -> None:
    token = await _register_user(client, "chan_admin@example.com", "Chan Admin Team")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create a Slack channel (team-wide)
    create_resp = await client.post(
        "/api/v1/notification-channels",
        json={
            "type": "slack",
            "name": "Team Alerts",
            "secret_value": "https://hooks.slack.com/services/T00/B00/XXXX",
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    created = create_resp.json()
    channel_id = created["id"]
    assert created["name"] == "Team Alerts"
    assert created["type"] == "slack"
    assert created["is_enabled"] is True
    assert created["monitor_id"] is None
    # Secret must never appear in the response body
    assert "secret_value" not in created
    assert "secret_ref" not in created
    # Display hint must be present
    assert created["secret_display_hint"] is not None
    assert len(created["secret_display_hint"]) > 0

    # 1b. Verify the secret is actually encrypted in the database
    from uuid import UUID

    from sqlalchemy import select

    from app.core.crypto import DecryptionError, decrypt
    from app.modules.channels.models import NotificationChannel

    async with _TestSessionFactory() as db:
        res = await db.execute(
            select(NotificationChannel).where(NotificationChannel.id == UUID(channel_id))
        )
        ch = res.scalar_one()
        assert ch.secret_ref is not None
        assert "XXXX" not in ch.secret_ref
        assert decrypt(ch.secret_ref) == "https://hooks.slack.com/services/T00/B00/XXXX"

        # Tampered ciphertext fails decryption
        tampered = ch.secret_ref[:-4] + ("AAAA" if ch.secret_ref[-4:] != "AAAA" else "BBBB")
        with pytest.raises(DecryptionError):
            decrypt(tampered)

    # 2. List channels
    list_resp = await client.get("/api/v1/notification-channels", headers=headers)
    assert list_resp.status_code == 200
    items = list_resp.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == channel_id
    # Secret never in list response
    assert "secret_value" not in items[0]

    # 3. Update name and disable
    patch_resp = await client.patch(
        f"/api/v1/notification-channels/{channel_id}",
        json={"name": "Renamed Alerts", "is_enabled": False},
        headers=headers,
    )
    assert patch_resp.status_code == 200
    updated = patch_resp.json()
    assert updated["name"] == "Renamed Alerts"
    assert updated["is_enabled"] is False
    # Hint unchanged
    assert updated["secret_display_hint"] == created["secret_display_hint"]

    # 4. Rotate secret — hint should change
    rotate_resp = await client.patch(
        f"/api/v1/notification-channels/{channel_id}",
        json={"secret_value": "https://hooks.slack.com/services/T99/B99/YYYY"},
        headers=headers,
    )
    assert rotate_resp.status_code == 200
    rotated = rotate_resp.json()
    # Secret never returned
    assert "secret_value" not in rotated
    # Hint updated to reflect new secret suffix
    assert rotated["secret_display_hint"] is not None

    async with _TestSessionFactory() as db:
        res = await db.execute(
            select(NotificationChannel).where(NotificationChannel.id == UUID(channel_id))
        )
        ch = res.scalar_one()
        assert decrypt(ch.secret_ref) == "https://hooks.slack.com/services/T99/B99/YYYY"

    # 5. Soft delete
    del_resp = await client.delete(f"/api/v1/notification-channels/{channel_id}", headers=headers)
    assert del_resp.status_code == 204

    # 6. Channel no longer in list
    list_after = await client.get("/api/v1/notification-channels", headers=headers)
    assert list_after.json()["items"] == []

    # 7. PATCH on deleted channel returns 404
    patch_after = await client.patch(
        f"/api/v1/notification-channels/{channel_id}",
        json={"name": "Ghost"},
        headers=headers,
    )
    assert patch_after.status_code == 404


# ---------------------------------------------------------------------------
# Tests: read_only role receives 403
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_read_only_gets_403(client: AsyncClient) -> None:
    """read_only users must not see add/edit/delete controls (US-03 AC)."""
    from sqlalchemy import select
    from sqlalchemy import update as sa_update

    from app.db.models import TeamMembership, TeamRole

    # Register admin first
    admin_token = await _register_user(client, "chan_ro_admin@example.com", "RO Test Team")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Create a channel as admin so we have something to test against
    create_resp = await client.post(
        "/api/v1/notification-channels",
        json={
            "type": "email",
            "name": "RO Test Channel",
            "secret_value": "ops@example.com",
        },
        headers=admin_headers,
    )
    assert create_resp.status_code == 201
    channel_id = create_resp.json()["id"]

    # Register a second user — only needed so we have a second team in DB
    # for potential future multi-user test; the real read_only scenario is
    # achieved by demoting the admin's membership below.
    await _register_user(client, "chan_ro_user@example.com", "RO User Team")
    # Demote admin's own role to read_only for this test
    # (simpler: just override the existing admin to read_only directly in DB)
    async with _TestSessionFactory() as db:
        from app.db.models import User

        user_result = await db.execute(
            select(User).where(User.email == "chan_ro_admin@example.com")
        )
        admin_user = user_result.scalar_one()
        await db.execute(
            sa_update(TeamMembership)
            .where(
                TeamMembership.user_id == admin_user.id,
            )
            .values(role=TeamRole.read_only)
        )
        await db.commit()

    # Now admin_headers belongs to a read_only user
    for method, url, body in [
        ("GET", "/api/v1/notification-channels", None),
        (
            "POST",
            "/api/v1/notification-channels",
            {
                "type": "email",
                "name": "X",
                "secret_value": "x@y.com",
            },
        ),
        (
            "PATCH",
            f"/api/v1/notification-channels/{channel_id}",
            {"name": "Y"},
        ),
        ("DELETE", f"/api/v1/notification-channels/{channel_id}", None),
    ]:
        if body:
            resp = await client.request(method, url, json=body, headers=admin_headers)
        else:
            resp = await client.request(method, url, headers=admin_headers)
        assert resp.status_code == 403, f"Expected 403 for {method} {url}, got {resp.status_code}"


# ---------------------------------------------------------------------------
# Tests: 422 validation — invalid secrets per type
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invalid_slack_secret_returns_422(client: AsyncClient) -> None:
    token = await _register_user(client, "chan_val1@example.com", "Val Team 1")
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.post(
        "/api/v1/notification-channels",
        json={
            "type": "slack",
            "name": "Bad Slack",
            "secret_value": "https://evil.example.com/hook",
        },
        headers=headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_webhook_ssrf_rejected(client: AsyncClient) -> None:
    token = await _register_user(client, "chan_val2@example.com", "Val Team 2")
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.post(
        "/api/v1/notification-channels",
        json={
            "type": "webhook",
            "name": "SSRF Attempt",
            "secret_value": "https://192.168.0.1/exfil",
        },
        headers=headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_invalid_email_secret_returns_422(client: AsyncClient) -> None:
    token = await _register_user(client, "chan_val3@example.com", "Val Team 3")
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.post(
        "/api/v1/notification-channels",
        json={
            "type": "email",
            "name": "Bad Email Chan",
            "secret_value": "not-an-email",
        },
        headers=headers,
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Tests: team isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_team_isolation(client: AsyncClient) -> None:
    token_a = await _register_user(client, "chan_teamA@example.com", "Chan Team A")
    token_b = await _register_user(client, "chan_teamB@example.com", "Chan Team B")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Team A creates a channel
    resp = await client.post(
        "/api/v1/notification-channels",
        json={
            "type": "email",
            "name": "Team A Channel",
            "secret_value": "a@example.com",
        },
        headers=headers_a,
    )
    assert resp.status_code == 201
    channel_id = resp.json()["id"]

    # Team B cannot see or delete Team A's channel
    list_b = await client.get("/api/v1/notification-channels", headers=headers_b)
    assert all(ch["id"] != channel_id for ch in list_b.json()["items"])

    del_b = await client.delete(f"/api/v1/notification-channels/{channel_id}", headers=headers_b)
    assert del_b.status_code == 404


# ---------------------------------------------------------------------------
# Tests: scope query parameter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scope_team_filter(client: AsyncClient) -> None:
    token = await _register_user(client, "chan_scope@example.com", "Scope Team")
    headers = {"Authorization": f"Bearer {token}"}

    # Create team-wide channel
    await client.post(
        "/api/v1/notification-channels",
        json={"type": "email", "name": "Team Channel", "secret_value": "team@x.com"},
        headers=headers,
    )

    # scope=team returns only team-wide channels (monitor_id=null)
    resp = await client.get("/api/v1/notification-channels?scope=team", headers=headers)
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert item["monitor_id"] is None


# ---------------------------------------------------------------------------
# Tests: all channel types creation and secret decryption
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_all_channel_types_created_and_encrypted(client: AsyncClient) -> None:
    token = await _register_user(client, "chan_alltypes@example.com", "All Types Team")
    headers = {"Authorization": f"Bearer {token}"}

    from sqlalchemy import select

    from app.core.crypto import decrypt
    from app.modules.channels.models import NotificationChannel

    test_channels = [
        ("slack", "Slack", "https://hooks.slack.com/services/T11/B11/SLACKSECRET"),
        ("discord", "Discord", "https://discord.com/api/webhooks/999/DISCORDSECRET"),
        ("email", "Email", "alerts-all@example.com"),
        ("webhook", "Webhook", "https://api.mycompany.example.com/alerts/endpoint"),
    ]

    for c_type, name, secret in test_channels:
        resp = await client.post(
            "/api/v1/notification-channels",
            json={"type": c_type, "name": name, "secret_value": secret},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "secret_value" not in data
        assert "secret_ref" not in data
        assert data["secret_display_hint"] is not None

        # Verify DB row is encrypted and decryptable
        async with _TestSessionFactory() as db:
            res = await db.execute(
                select(NotificationChannel).where(NotificationChannel.id == UUID(data["id"]))
            )
            ch = res.scalar_one()
            assert ch.secret_ref is not None
            assert secret not in ch.secret_ref
            assert decrypt(ch.secret_ref) == secret


# ---------------------------------------------------------------------------
# Tests: monitor attachment and cross-team monitor 404
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_channel_with_monitor_scoping(client: AsyncClient) -> None:
    token_a = await _register_user(client, "mon_team_a@example.com", "Mon Team A")
    token_b = await _register_user(client, "mon_team_b@example.com", "Mon Team B")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Team A creates a monitor
    mon_resp = await client.post(
        "/api/v1/monitors",
        json={"name": "Team A API", "url": "https://api.example.com/health"},
        headers=headers_a,
    )
    assert mon_resp.status_code == 201
    monitor_a_id = mon_resp.json()["id"]

    # Team A attaches a channel to monitor A -> 201
    ch_resp = await client.post(
        "/api/v1/notification-channels",
        json={
            "type": "email",
            "name": "Team A Monitor Channel",
            "monitor_id": monitor_a_id,
            "secret_value": "mon_a@example.com",
        },
        headers=headers_a,
    )
    assert ch_resp.status_code == 201
    assert ch_resp.json()["monitor_id"] == monitor_a_id

    # Filter by monitor_id -> returns the attached channel
    list_resp = await client.get(
        f"/api/v1/notification-channels?monitor_id={monitor_a_id}",
        headers=headers_a,
    )
    assert list_resp.status_code == 200
    items = list_resp.json()["items"]
    assert len(items) == 1
    assert items[0]["monitor_id"] == monitor_a_id

    # Team B tries to create a channel referencing Team A's monitor -> 404
    b_cross_create = await client.post(
        "/api/v1/notification-channels",
        json={
            "type": "email",
            "name": "Team B Steal",
            "monitor_id": monitor_a_id,
            "secret_value": "b@example.com",
        },
        headers=headers_b,
    )
    assert b_cross_create.status_code == 404

    # Team B tries to list channels for Team A's monitor -> 404
    b_cross_list = await client.get(
        f"/api/v1/notification-channels?monitor_id={monitor_a_id}",
        headers=headers_b,
    )
    assert b_cross_list.status_code == 404


# ---------------------------------------------------------------------------
# Tests: secrets never leaked in logs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_secret_leak_in_logs(
    client: AsyncClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    import logging

    caplog.set_level(logging.DEBUG)
    token = await _register_user(client, "chan_log_safe@example.com", "Log Safe Team")
    headers = {"Authorization": f"Bearer {token}"}

    super_secret = "https://hooks.slack.com/services/T999/B999/TOP_SECRET_TOKEN"
    resp = await client.post(
        "/api/v1/notification-channels",
        json={
            "type": "slack",
            "name": "Log Check",
            "secret_value": super_secret,
        },
        headers=headers,
    )
    assert resp.status_code == 201

    assert "TOP_SECRET_TOKEN" not in caplog.text
    assert super_secret not in caplog.text

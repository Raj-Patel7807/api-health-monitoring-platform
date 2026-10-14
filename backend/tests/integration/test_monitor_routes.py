"""Integration tests for monitor CRUD endpoints (US-02, US-19).

Uses an async SQLite in-memory database to exercise real route handling,
database persistence, authentication, team scoping, RBAC, and soft delete.
"""

from collections.abc import AsyncGenerator, Generator
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models import TeamMembership, TeamRole
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

    cfg.get_settings.cache_clear()
    monkeypatch.setenv("JWT_SECRET_KEY", _TEST_SECRET)
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
    monkeypatch.setenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")
    yield
    cfg.get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Helper: register a user and return their access token
# ---------------------------------------------------------------------------


async def _register_user(
    client: AsyncClient,
    email: str,
    team_name: str,
) -> str:
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
# Tests: Monitor CRUD & Soft Delete Lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_monitor_crud_lifecycle(client: AsyncClient) -> None:
    token = await _register_user(client, "alice_mon@example.com", "Alice Engineering")
    auth_headers = {"Authorization": f"Bearer {token}"}

    # 1. Create a monitor
    create_payload = {
        "name": "Payments API",
        "url": "https://api.payments.example.com/health",
        "method": "GET",
        "check_interval_seconds": 60,
        "timeout_seconds": 10,
        "expected_status_code": 200,
        "failure_threshold": 3,
        "recovery_threshold": 2,
    }
    create_resp = await client.post("/api/v1/monitors", json=create_payload, headers=auth_headers)
    assert create_resp.status_code == 201
    created = create_resp.json()
    monitor_id = created["id"]
    assert created["name"] == "Payments API"
    assert created["url"] == "https://api.payments.example.com/health"
    assert created["method"] == "GET"
    assert created["enabled"] is True
    assert created["check_interval_seconds"] == 60
    assert created["current_interval_seconds"] == 60
    assert created["consecutive_failures"] == 0
    assert created["consecutive_successes"] == 0

    # 2. List monitors
    list_resp = await client.get("/api/v1/monitors", headers=auth_headers)
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] == 1
    assert len(list_data["items"]) == 1
    assert list_data["items"][0]["id"] == monitor_id

    # 3. Get monitor detail by ID
    get_resp = await client.get(f"/api/v1/monitors/{monitor_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == monitor_id

    # 4. Partially update monitor
    patch_payload = {
        "name": "Updated Payments API",
        "check_interval_seconds": 120,
        "timeout_seconds": 15,
        "expected_status_code": 204,
    }
    patch_resp = await client.patch(
        f"/api/v1/monitors/{monitor_id}",
        json=patch_payload,
        headers=auth_headers,
    )
    assert patch_resp.status_code == 200
    patched = patch_resp.json()
    assert patched["name"] == "Updated Payments API"
    assert patched["check_interval_seconds"] == 120
    assert patched["current_interval_seconds"] == 120
    assert patched["timeout_seconds"] == 15
    assert patched["expected_status_code"] == 204

    # 5. Soft delete monitor
    del_resp = await client.delete(f"/api/v1/monitors/{monitor_id}", headers=auth_headers)
    assert del_resp.status_code == 204

    # 6. Verify monitor is no longer visible
    get_after_del = await client.get(f"/api/v1/monitors/{monitor_id}", headers=auth_headers)
    assert get_after_del.status_code == 404

    # 7. Verify list shows 0 items
    list_after_del = await client.get("/api/v1/monitors", headers=auth_headers)
    assert list_after_del.status_code == 200
    assert list_after_del.json()["total"] == 0

    # 8. Deleting again returns 404
    del_again = await client.delete(f"/api/v1/monitors/{monitor_id}", headers=auth_headers)
    assert del_again.status_code == 404


# ---------------------------------------------------------------------------
# Tests: Team Scoping and Multi-tenant Isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_team_scoping_isolation(client: AsyncClient) -> None:
    token_a = await _register_user(client, "team_a_user@example.com", "Team Alpha")
    token_b = await _register_user(client, "team_b_user@example.com", "Team Beta")

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Team Alpha creates a monitor
    r_a = await client.post(
        "/api/v1/monitors",
        json={"name": "Alpha API", "url": "https://alpha.example.com"},
        headers=headers_a,
    )
    assert r_a.status_code == 201
    alpha_mon_id = r_a.json()["id"]

    # Team Beta creates a monitor
    r_b = await client.post(
        "/api/v1/monitors",
        json={"name": "Beta API", "url": "https://beta.example.com"},
        headers=headers_b,
    )
    assert r_b.status_code == 201
    beta_mon_id = r_b.json()["id"]

    # Team Alpha lists monitors: only sees Alpha
    list_a = await client.get("/api/v1/monitors", headers=headers_a)
    ids_a = [m["id"] for m in list_a.json()["items"]]
    assert alpha_mon_id in ids_a
    assert beta_mon_id not in ids_a

    # Team Beta lists monitors: only sees Beta
    list_b = await client.get("/api/v1/monitors", headers=headers_b)
    ids_b = [m["id"] for m in list_b.json()["items"]]
    assert beta_mon_id in ids_b
    assert alpha_mon_id not in ids_b

    # Team Beta attempts to GET Team Alpha's monitor -> 404
    cross_get = await client.get(f"/api/v1/monitors/{alpha_mon_id}", headers=headers_b)
    assert cross_get.status_code == 404

    # Team Beta attempts to PATCH Team Alpha's monitor -> 404
    cross_patch = await client.patch(
        f"/api/v1/monitors/{alpha_mon_id}",
        json={"name": "Hacked"},
        headers=headers_b,
    )
    assert cross_patch.status_code == 404

    # Team Beta attempts to DELETE Team Alpha's monitor -> 404
    cross_del = await client.delete(f"/api/v1/monitors/{alpha_mon_id}", headers=headers_b)
    assert cross_del.status_code == 404


# ---------------------------------------------------------------------------
# Tests: RBAC Authorization
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rbac_read_only_member_cannot_modify(client: AsyncClient) -> None:
    admin_token = await _register_user(client, "admin_rbac@example.com", "RBAC Team")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Admin creates a monitor
    create_resp = await client.post(
        "/api/v1/monitors",
        json={"name": "RBAC Mon", "url": "https://rbac.example.com"},
        headers=admin_headers,
    )
    assert create_resp.status_code == 201
    mon_id = create_resp.json()["id"]

    # Register another user and attach them to the same team as read_only
    ro_token = await _register_user(client, "readonly_user@example.com", "ReadOnly Separate Team")

    # Change membership role in DB for this user to be on the admin's team with role read_only
    admin_mon_detail = create_resp.json()
    team_id = admin_mon_detail["team_id"]

    # Fetch read_only user id via /auth/me
    me_resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {ro_token}"},
    )
    ro_user_id = me_resp.json()["id"]

    from uuid import UUID

    # Directly insert read_only membership into DB session
    async with _TestSessionFactory() as session:
        membership = TeamMembership(
            id=uuid4(),
            team_id=UUID(str(team_id)),
            user_id=UUID(str(ro_user_id)),
            role=TeamRole.read_only,
        )
        session.add(membership)
        await session.commit()

    ro_headers = {
        "Authorization": f"Bearer {ro_token}",
        "X-Team-ID": str(team_id),
    }

    # Read-only user can list monitors
    ro_list = await client.get("/api/v1/monitors", headers=ro_headers)
    assert ro_list.status_code == 200
    assert ro_list.json()["total"] == 1

    # Read-only user can view monitor detail
    ro_get = await client.get(f"/api/v1/monitors/{mon_id}", headers=ro_headers)
    assert ro_get.status_code == 200

    # Read-only user CANNOT create a monitor -> 403
    ro_create = await client.post(
        "/api/v1/monitors",
        json={"name": "Forbidden Mon", "url": "https://forbidden.example.com"},
        headers=ro_headers,
    )
    assert ro_create.status_code == 403

    # Read-only user CANNOT update a monitor -> 403
    ro_patch = await client.patch(
        f"/api/v1/monitors/{mon_id}",
        json={"name": "Hacked"},
        headers=ro_headers,
    )
    assert ro_patch.status_code == 403

    # Read-only user CANNOT delete a monitor -> 403
    ro_del = await client.delete(f"/api/v1/monitors/{mon_id}", headers=ro_headers)
    assert ro_del.status_code == 403


# ---------------------------------------------------------------------------
# Tests: Request Validation Errors (HTTP 422)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validation_errors(client: AsyncClient) -> None:
    token = await _register_user(client, "val_user@example.com", "Val Team")
    headers = {"Authorization": f"Bearer {token}"}

    # Invalid URL scheme
    r1 = await client.post(
        "/api/v1/monitors",
        json={"name": "Bad URL", "url": "ftp://bad.example.com"},
        headers=headers,
    )
    assert r1.status_code == 422

    # Timeout > Interval
    r2 = await client.post(
        "/api/v1/monitors",
        json={
            "name": "Bad Timeout",
            "url": "https://example.com",
            "check_interval_seconds": 10,
            "timeout_seconds": 15,
        },
        headers=headers,
    )
    assert r2.status_code == 422

    # Bad HTTP method
    r3 = await client.post(
        "/api/v1/monitors",
        json={"name": "Bad Method", "url": "https://example.com", "method": "INVALID"},
        headers=headers,
    )
    assert r3.status_code == 422

    # Malformed UUID in path
    r4 = await client.get("/api/v1/monitors/not-a-uuid", headers=headers)
    assert r4.status_code == 422


# ---------------------------------------------------------------------------
# Tests: Authentication Guard (HTTP 401)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unauthenticated_request_rejected(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/monitors")
    assert resp.status_code in (401, 403)

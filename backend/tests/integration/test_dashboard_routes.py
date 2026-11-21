"""Integration tests for Dashboard endpoint (US-13, Issue #66).

Uses an async SQLite in-memory database to test the dashboard endpoint:
- Authentication & RBAC (admin, operator, read_only can view; unauthenticated 401)
- Derived status logic (healthy, failing, unknown)
- Disabled and soft-deleted monitors excluded
- Summary counts accuracy
- Open incident ID returned
- Ordering (failing monitors first)
- Team isolation
"""

from collections.abc import AsyncGenerator, Generator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models import TeamMembership, TeamRole
from app.db.session import get_db
from app.main import app
from app.modules.incidents.models import Incident
from app.modules.monitors.models import Monitor
from app.modules.results.models import HealthCheckResult

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


async def _register_user(
    client: AsyncClient,
    email: str,
    team_name: str,
    full_name: str = "Test User",
) -> dict:
    resp = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "full_name": full_name,
            "password": "password123",
            "team_name": team_name,
        },
    )
    assert resp.status_code == 201
    auth_data = resp.json()
    token = auth_data["access_token"]
    me_resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    user_data = me_resp.json()
    return {
        "access_token": token,
        "refresh_token": auth_data["refresh_token"],
        "user": user_data,
    }


# ---------------------------------------------------------------------------
# Dashboard Integration Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dashboard_unauthenticated(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/dashboard")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_dashboard_empty_for_new_team(client: AsyncClient) -> None:
    auth_data = await _register_user(client, "dash_empty@example.com", "Empty Team")
    headers = {"Authorization": f"Bearer {auth_data['access_token']}"}

    resp = await client.get("/api/v1/dashboard", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["monitors"] == []
    assert data["summary"] == {
        "total_monitors": 0,
        "healthy": 0,
        "failing": 0,
        "unknown": 0,
        "open_incidents": 0,
    }


@pytest.mark.asyncio
async def test_dashboard_monitors_status_and_ordering(client: AsyncClient) -> None:
    auth_data = await _register_user(client, "dash_monitors@example.com", "Active Team")
    token = auth_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Get team_id
    me = await client.get("/api/v1/auth/me", headers=headers)
    user_id = UUID(me.json()["id"])

    # Look up team_id from DB
    async with _TestSessionFactory() as session:
        membership = await session.get(
            TeamMembership,
            (
                await session.execute(
                    Base.metadata.tables["team_memberships"]
                    .select()
                    .where(Base.metadata.tables["team_memberships"].c.user_id == user_id)
                )
            )
            .first()
            .id,
        )
        team_id = membership.team_id

        # Insert monitors:
        # 1. Healthy monitor
        m_healthy = Monitor(
            id=uuid4(),
            team_id=team_id,
            name="Healthy Service",
            url="https://healthy.example.com",
            enabled=True,
        )
        # 2. Failing monitor with open incident
        m_failing = Monitor(
            id=uuid4(),
            team_id=team_id,
            name="Failing Service",
            url="https://failing.example.com",
            enabled=True,
        )
        # 3. Unknown monitor (no checks)
        m_unknown = Monitor(
            id=uuid4(),
            team_id=team_id,
            name="Unknown Service",
            url="https://unknown.example.com",
            enabled=True,
        )
        # 4. Disabled monitor
        m_disabled = Monitor(
            id=uuid4(),
            team_id=team_id,
            name="Disabled Service",
            url="https://disabled.example.com",
            enabled=False,
        )
        # 5. Soft-deleted monitor
        m_deleted = Monitor(
            id=uuid4(),
            team_id=team_id,
            name="Deleted Service",
            url="https://deleted.example.com",
            enabled=True,
            deleted_at=datetime.now(UTC),
        )
        session.add_all([m_healthy, m_failing, m_unknown, m_disabled, m_deleted])
        await session.commit()

        # Add health check results within window
        now = datetime.now(UTC)
        r_healthy = HealthCheckResult(
            id=uuid4(),
            monitor_id=m_healthy.id,
            status="healthy",
            response_time_ms=45,
            checked_at=now - timedelta(minutes=5),
        )
        r_failing = HealthCheckResult(
            id=uuid4(),
            monitor_id=m_failing.id,
            status="failing",
            response_time_ms=1200,
            checked_at=now - timedelta(minutes=2),
        )
        session.add_all([r_healthy, r_failing])

        # Add open incident for m_failing
        inc = Incident(
            id=uuid4(),
            monitor_id=m_failing.id,
            status="open",
            opened_at=now - timedelta(minutes=2),
            failure_count=3,
        )
        session.add(inc)
        await session.commit()
        open_inc_id = inc.id

    # Call GET /api/v1/dashboard
    resp = await client.get("/api/v1/dashboard", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["summary"] == {
        "total_monitors": 3,
        "healthy": 1,
        "failing": 1,
        "unknown": 1,
        "open_incidents": 1,
    }

    monitors = data["monitors"]
    assert len(monitors) == 3

    # Failing monitor must be first
    assert monitors[0]["id"] == str(m_failing.id)
    assert monitors[0]["status"] == "failing"
    assert monitors[0]["open_incident_id"] == str(open_inc_id)
    assert monitors[0]["last_response_time_ms"] == 1200

    # Remaining monitors
    remaining_ids = {m["id"] for m in monitors[1:]}
    assert remaining_ids == {str(m_healthy.id), str(m_unknown.id)}

    m_healthy_resp = next(m for m in monitors if m["id"] == str(m_healthy.id))
    assert m_healthy_resp["status"] == "healthy"
    assert m_healthy_resp["open_incident_id"] is None
    assert m_healthy_resp["last_response_time_ms"] == 45

    m_unknown_resp = next(m for m in monitors if m["id"] == str(m_unknown.id))
    assert m_unknown_resp["status"] == "unknown"
    assert m_unknown_resp["open_incident_id"] is None
    assert m_unknown_resp["last_checked_at"] is None
    assert m_unknown_resp["last_response_time_ms"] is None


@pytest.mark.asyncio
async def test_dashboard_team_isolation(client: AsyncClient) -> None:
    # Team 1
    t1_data = await _register_user(client, "dash_team1@example.com", "Team One")
    h1 = {"Authorization": f"Bearer {t1_data['access_token']}"}

    # Team 2
    t2_data = await _register_user(client, "dash_team2@example.com", "Team Two")
    h2 = {"Authorization": f"Bearer {t2_data['access_token']}"}

    # Team 1 creates a monitor
    resp = await client.post(
        "/api/v1/monitors",
        json={"name": "T1 Monitor", "url": "https://t1.example.com"},
        headers=h1,
    )
    assert resp.status_code == 201
    t1_mon_id = resp.json()["id"]

    # Team 1 dashboard sees 1 monitor
    d1 = await client.get("/api/v1/dashboard", headers=h1)
    assert d1.status_code == 200
    assert d1.json()["summary"]["total_monitors"] == 1
    assert d1.json()["monitors"][0]["id"] == t1_mon_id

    # Team 2 dashboard sees 0 monitors
    d2 = await client.get("/api/v1/dashboard", headers=h2)
    assert d2.status_code == 200
    assert d2.json()["summary"]["total_monitors"] == 0
    assert d2.json()["monitors"] == []


@pytest.mark.asyncio
async def test_dashboard_rbac_all_roles(client: AsyncClient) -> None:
    # Register admin
    admin_data = await _register_user(client, "admin_dash@example.com", "RBAC Dash Team")
    admin_token = admin_data["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Get team_id
    me_resp = await client.get("/api/v1/auth/me", headers=admin_headers)
    admin_user_id = UUID(me_resp.json()["id"])

    async with _TestSessionFactory() as session:
        membership = (
            await session.execute(
                Base.metadata.tables["team_memberships"]
                .select()
                .where(Base.metadata.tables["team_memberships"].c.user_id == admin_user_id)
            )
        ).first()
        team_id = membership.team_id

    # Register operator user and attach to same team
    op_data = await _register_user(client, "op_dash@example.com", "Op Separate Team")
    op_user_id = UUID(op_data["user"]["id"])

    # Register read_only user and attach to same team
    ro_data = await _register_user(client, "ro_dash@example.com", "RO Separate Team")
    ro_user_id = UUID(ro_data["user"]["id"])

    async with _TestSessionFactory() as session:
        session.add(
            TeamMembership(
                id=uuid4(),
                team_id=team_id,
                user_id=op_user_id,
                role=TeamRole.operator,
            )
        )
        session.add(
            TeamMembership(
                id=uuid4(),
                team_id=team_id,
                user_id=ro_user_id,
                role=TeamRole.read_only,
            )
        )
        await session.commit()

    op_headers = {"Authorization": f"Bearer {op_data['access_token']}", "X-Team-ID": str(team_id)}
    ro_headers = {"Authorization": f"Bearer {ro_data['access_token']}", "X-Team-ID": str(team_id)}

    # Admin: 200
    r_admin = await client.get("/api/v1/dashboard", headers=admin_headers)
    assert r_admin.status_code == 200

    # Operator: 200
    r_op = await client.get("/api/v1/dashboard", headers=op_headers)
    assert r_op.status_code == 200

    # Read-only: 200
    r_ro = await client.get("/api/v1/dashboard", headers=ro_headers)
    assert r_ro.status_code == 200

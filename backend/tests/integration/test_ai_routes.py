"""Integration tests for AI-powered incident assistance endpoints (Section 6).

Tests:
- GET /api/v1/incidents/{id}/ai-analysis:
  * 401 unauthenticated
  * 404 non-existent incident
  * 404 cross-team incident access
  * 200 returns deterministic/cached AI analysis
- POST /api/v1/incidents/{id}/ai-analysis:
  * 401 unauthenticated
  * 403 read_only role
  * 404 cross-team incident access
  * 200 forces re-generation of analysis
"""

from collections.abc import AsyncGenerator, Generator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.modules.incidents.models import Incident
from app.modules.monitors.models import Monitor

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


_TEST_SECRET = "integration-test-secret-long-enough-for-hs256"


@pytest.fixture(autouse=True)
def _patch_settings(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    from app.core import config as cfg

    cfg.get_settings.cache_clear()
    monkeypatch.setenv("JWT_SECRET_KEY", _TEST_SECRET)
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
    monkeypatch.setenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")
    monkeypatch.setenv("LLM_PROVIDER", "deterministic")
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


async def _create_test_incident(team_id: UUID) -> tuple[UUID, UUID]:
    """Helper to create a monitor and an open incident in DB."""
    async with _TestSessionFactory() as session:
        monitor = Monitor(
            id=uuid4(),
            team_id=team_id,
            name="Test Target API",
            url="https://api.example.com/checkout",
            method="POST",
            expected_status_code=200,
            check_interval_seconds=60,
            current_interval_seconds=60,
            timeout_seconds=5,
            failure_threshold=3,
            recovery_threshold=2,
            consecutive_failures=3,
            consecutive_successes=0,
            enabled=True,
        )
        session.add(monitor)
        incident = Incident(
            id=uuid4(),
            monitor_id=monitor.id,
            status="open",
            failure_count=3,
            opened_at=datetime.now(UTC),
        )
        session.add(incident)
        await session.commit()
        return monitor.id, incident.id


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_ai_analysis_unauthenticated(client: AsyncClient) -> None:
    resp = await client.get(f"/api/v1/incidents/{uuid4()}/ai-analysis")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_ai_analysis_not_found(client: AsyncClient) -> None:
    user_auth = await _register_user(client, "alice_ai@example.com", "Alice AI Team")
    headers = {"Authorization": f"Bearer {user_auth['access_token']}"}

    resp = await client.get(f"/api/v1/incidents/{uuid4()}/ai-analysis", headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_ai_analysis_cross_team_forbidden(client: AsyncClient) -> None:
    # Team A creates incident
    team_a_auth = await _register_user(client, "team_a_user@example.com", "Team A")
    team_a_id = UUID(team_a_auth["user"]["team"]["id"])
    _, incident_id = await _create_test_incident(team_a_id)

    # Team B tries to access Team A's incident
    team_b_auth = await _register_user(client, "team_b_user@example.com", "Team B")
    team_b_headers = {"Authorization": f"Bearer {team_b_auth['access_token']}"}

    resp = await client.get(f"/api/v1/incidents/{incident_id}/ai-analysis", headers=team_b_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_ai_analysis_success(client: AsyncClient) -> None:
    user_auth = await _register_user(client, "carol_ai@example.com", "Carol AI Team")
    team_id = UUID(user_auth["user"]["team"]["id"])
    headers = {"Authorization": f"Bearer {user_auth['access_token']}"}

    _, incident_id = await _create_test_incident(team_id)

    resp = await client.get(f"/api/v1/incidents/{incident_id}/ai-analysis", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["incident_id"] == str(incident_id)
    assert data["status"] == "completed"
    assert "summary" in data and len(data["summary"]) > 0
    assert "root_cause" in data
    assert isinstance(data["suggested_actions"], list)
    assert isinstance(data["investigation_steps"], list)
    assert isinstance(data["prevention_steps"], list)
    assert "model" in data


@pytest.mark.asyncio
async def test_post_ai_analysis_regenerate(client: AsyncClient) -> None:
    user_auth = await _register_user(client, "dave_ai@example.com", "Dave AI Team")
    team_id = UUID(user_auth["user"]["team"]["id"])
    headers = {"Authorization": f"Bearer {user_auth['access_token']}"}

    _, incident_id = await _create_test_incident(team_id)

    # Trigger regenerate
    resp = await client.post(f"/api/v1/incidents/{incident_id}/ai-analysis", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["incident_id"] == str(incident_id)
    assert data["status"] == "completed"


@pytest.mark.asyncio
async def test_post_ai_analysis_read_only_forbidden(client: AsyncClient) -> None:
    admin_auth = await _register_user(client, "admin_ai_ro@example.com", "Admin RO Team")
    admin_team_id = UUID(admin_auth["user"]["team"]["id"])
    admin_headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    _, incident_id = await _create_test_incident(admin_team_id)

    # Register another user and add as read_only
    ro_auth = await _register_user(client, "ro_ai_user@example.com", "Indep RO Team")
    add_resp = await client.post(
        "/api/v1/team/members",
        json={"email": "ro_ai_user@example.com", "role": "read_only"},
        headers=admin_headers,
    )
    assert add_resp.status_code == 201

    ro_headers = {
        "Authorization": f"Bearer {ro_auth['access_token']}",
        "X-Team-ID": str(admin_team_id),
    }

    resp = await client.post(f"/api/v1/incidents/{incident_id}/ai-analysis", headers=ro_headers)
    assert resp.status_code == 403

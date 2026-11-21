"""Integration tests for the monitor results API (US-08)."""

from collections.abc import AsyncGenerator, Generator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.modules.results.models import HealthCheckResult

_SQLITE_URL = "sqlite+aiosqlite:///:memory:"
_engine = create_async_engine(_SQLITE_URL, echo=False)
_TestSessionFactory = async_sessionmaker(_engine, expire_on_commit=False)

_TEST_SECRET = "integration-test-secret-long-enough-for-hs256"


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

    await _engine.dispose()


@pytest_asyncio.fixture()
async def client() -> AsyncGenerator[AsyncClient, None]:
    app.dependency_overrides[get_db] = _override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


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
) -> str:
    response = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "full_name": "Test User",
            "password": "password123",
            "team_name": team_name,
        },
    )

    assert response.status_code == 201, response.text
    return str(response.json()["access_token"])


async def _create_monitor(
    client: AsyncClient,
    token: str,
) -> str:
    response = await client.post(
        "/api/v1/monitors",
        json={
            "name": "Results Integration Monitor",
            "url": "https://example.com/health",
            "method": "GET",
            "check_interval_seconds": 60,
            "timeout_seconds": 10,
            "expected_status_code": 200,
            "failure_threshold": 3,
            "recovery_threshold": 2,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201, response.text
    return str(response.json()["id"])


async def _insert_results(monitor_id: str) -> list[HealthCheckResult]:
    monitor_uuid = UUID(monitor_id)
    now = datetime.now(UTC)

    rows = [
        HealthCheckResult(
            id=uuid4(),
            monitor_id=monitor_uuid,
            checked_at=now - timedelta(minutes=2),
            status="healthy",
            http_status_code=200,
            response_time_ms=120,
            timeout=False,
            connection_error=False,
            ssl_error=False,
            error_message=None,
            response_body_excerpt="",
        ),
        HealthCheckResult(
            id=uuid4(),
            monitor_id=monitor_uuid,
            checked_at=now - timedelta(minutes=1),
            status="failing",
            http_status_code=500,
            response_time_ms=250,
            timeout=False,
            connection_error=False,
            ssl_error=False,
            error_message="Server error",
            response_body_excerpt="Internal Server Error",
        ),
    ]

    async with _TestSessionFactory() as session:
        session.add_all(rows)
        await session.commit()

    return rows


@pytest.mark.asyncio
async def test_get_results_returns_persisted_records(client: AsyncClient) -> None:
    token = await _register_user(
        client,
        "results_user@example.com",
        "Results Team",
    )
    monitor_id = await _create_monitor(client, token)
    await _insert_results(monitor_id)

    response = await client.get(
        f"/api/v1/monitors/{monitor_id}/results",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200, response.text

    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["items"][0]["status"] == "failing"
    assert data["items"][1]["status"] == "healthy"


@pytest.mark.asyncio
async def test_get_results_filters_by_status(client: AsyncClient) -> None:
    token = await _register_user(
        client,
        "filter_user@example.com",
        "Filter Team",
    )
    monitor_id = await _create_monitor(client, token)
    await _insert_results(monitor_id)

    response = await client.get(
        f"/api/v1/monitors/{monitor_id}/results?status=healthy",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200, response.text

    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["status"] == "healthy"


@pytest.mark.asyncio
async def test_get_results_returns_empty_list_when_no_results(
    client: AsyncClient,
) -> None:
    token = await _register_user(
        client,
        "empty_user@example.com",
        "Empty Results Team",
    )
    monitor_id = await _create_monitor(client, token)

    response = await client.get(
        f"/api/v1/monitors/{monitor_id}/results",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200, response.text

    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_other_team_cannot_access_monitor_results(
    client: AsyncClient,
) -> None:
    owner_token = await _register_user(
        client,
        "owner_results@example.com",
        "Owner Results Team",
    )
    other_token = await _register_user(
        client,
        "other_results@example.com",
        "Other Results Team",
    )

    monitor_id = await _create_monitor(client, owner_token)
    await _insert_results(monitor_id)

    response = await client.get(
        f"/api/v1/monitors/{monitor_id}/results",
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert response.status_code == 404

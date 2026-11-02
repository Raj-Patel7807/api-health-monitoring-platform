"""Unit tests for monitor router endpoints with mock dependencies (US-02)."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.models import Team, TeamMembership, TeamRole, User
from app.db.session import get_db
from app.main import app
from app.modules.monitors.dependencies import (
    TeamContext,
    require_monitor_read,
    require_monitor_write,
)
from app.modules.monitors.models import Monitor

_NOW = datetime.now(UTC)


def _make_dummy_monitor(team_id: object = None, monitor_id: object = None) -> Monitor:
    return Monitor(
        id=monitor_id or uuid4(),
        team_id=team_id or uuid4(),
        name="Test API",
        url="https://api.example.com",
        method="GET",
        enabled=True,
        check_interval_seconds=60,
        current_interval_seconds=60,
        timeout_seconds=10,
        expected_status_code=200,
        failure_threshold=3,
        recovery_threshold=2,
        consecutive_failures=0,
        consecutive_successes=0,
        user_agent="APIMonitor/1.0",
        next_check_at=_NOW,
        created_at=_NOW,
        updated_at=_NOW,
    )


@pytest.fixture()
def mock_team_context() -> TeamContext:
    user = User(id=uuid4(), email="admin@example.com", full_name="Admin", password_hash="h")
    team = Team(id=uuid4(), name="Test Team")
    return TeamContext(user=user, team=team, role=TeamRole.admin)


@pytest.mark.asyncio
async def test_create_monitor_endpoint_success(mock_team_context: TeamContext) -> None:
    app.dependency_overrides[require_monitor_write] = lambda: mock_team_context
    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    dummy = _make_dummy_monitor(team_id=mock_team_context.team.id)

    with patch("app.modules.monitors.service.create_monitor", new=AsyncMock(return_value=dummy)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/api/v1/monitors",
                json={"name": "Test API", "url": "https://api.example.com"},
            )
            assert resp.status_code == 201
            data = resp.json()
            assert data["id"] == str(dummy.id)
            assert data["name"] == "Test API"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_monitor_cross_team_unauthorized(mock_team_context: TeamContext) -> None:
    app.dependency_overrides[require_monitor_write] = lambda: mock_team_context
    mock_db = AsyncMock()
    # Execute returns empty result for cross-team check
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    app.dependency_overrides[get_db] = lambda: mock_db

    other_team_id = str(uuid4())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/monitors",
            json={
                "name": "Test API",
                "url": "https://api.example.com",
                "team_id": other_team_id,
            },
        )
        assert resp.status_code == 403

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_monitor_cross_team_authorized(mock_team_context: TeamContext) -> None:
    app.dependency_overrides[require_monitor_write] = lambda: mock_team_context
    other_team_id = uuid4()
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_membership = TeamMembership(
        id=uuid4(),
        team_id=other_team_id,
        user_id=mock_team_context.user.id,
        role=TeamRole.admin,
    )
    mock_result.scalar_one_or_none.return_value = mock_membership
    mock_db.execute.return_value = mock_result
    app.dependency_overrides[get_db] = lambda: mock_db

    dummy = _make_dummy_monitor(team_id=other_team_id)

    with patch("app.modules.monitors.service.create_monitor", new=AsyncMock(return_value=dummy)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/api/v1/monitors",
                json={
                    "name": "Test API",
                    "url": "https://api.example.com",
                    "team_id": str(other_team_id),
                },
            )
            assert resp.status_code == 201

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_monitors_endpoint(mock_team_context: TeamContext) -> None:
    app.dependency_overrides[require_monitor_read] = lambda: mock_team_context
    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    dummy = _make_dummy_monitor(team_id=mock_team_context.team.id)

    with patch(
        "app.modules.monitors.service.list_monitors",
        new=AsyncMock(return_value=([dummy], 1)),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/monitors?page=1&page_size=20")
            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] == 1
            assert len(data["items"]) == 1
            assert data["items"][0]["name"] == "Test API"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_monitor_endpoint_found_and_not_found(mock_team_context: TeamContext) -> None:
    app.dependency_overrides[require_monitor_read] = lambda: mock_team_context
    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    dummy = _make_dummy_monitor(team_id=mock_team_context.team.id)

    # 1. Found
    with patch("app.modules.monitors.service.get_monitor", new=AsyncMock(return_value=dummy)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get(f"/api/v1/monitors/{dummy.id}")
            assert resp.status_code == 200
            assert resp.json()["id"] == str(dummy.id)

    # 2. Not found
    with patch("app.modules.monitors.service.get_monitor", new=AsyncMock(return_value=None)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get(f"/api/v1/monitors/{uuid4()}")
            assert resp.status_code == 404

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_update_monitor_endpoint_found_and_not_found(mock_team_context: TeamContext) -> None:
    app.dependency_overrides[require_monitor_write] = lambda: mock_team_context
    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    dummy = _make_dummy_monitor(team_id=mock_team_context.team.id)
    dummy_updated = _make_dummy_monitor(team_id=mock_team_context.team.id, monitor_id=dummy.id)
    dummy_updated.name = "Patched Name"

    # 1. Found
    with (
        patch("app.modules.monitors.service.get_monitor", new=AsyncMock(return_value=dummy)),
        patch(
            "app.modules.monitors.service.update_monitor", new=AsyncMock(return_value=dummy_updated)
        ),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.patch(
                f"/api/v1/monitors/{dummy.id}",
                json={"name": "Patched Name"},
            )
            assert resp.status_code == 200
            assert resp.json()["name"] == "Patched Name"

    # 2. Not found
    with patch("app.modules.monitors.service.get_monitor", new=AsyncMock(return_value=None)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.patch(
                f"/api/v1/monitors/{uuid4()}",
                json={"name": "Patched Name"},
            )
            assert resp.status_code == 404

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_delete_monitor_endpoint_found_and_not_found(mock_team_context: TeamContext) -> None:
    app.dependency_overrides[require_monitor_write] = lambda: mock_team_context
    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    dummy = _make_dummy_monitor(team_id=mock_team_context.team.id)

    # 1. Found -> 204
    with (
        patch("app.modules.monitors.service.get_monitor", new=AsyncMock(return_value=dummy)),
        patch("app.modules.monitors.service.soft_delete_monitor", new=AsyncMock()) as mock_delete,
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.delete(f"/api/v1/monitors/{dummy.id}")
            assert resp.status_code == 204
            mock_delete.assert_awaited_once_with(mock_db, dummy)

    # 2. Not found -> 404
    with patch("app.modules.monitors.service.get_monitor", new=AsyncMock(return_value=None)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.delete(f"/api/v1/monitors/{uuid4()}")
            assert resp.status_code == 404

    app.dependency_overrides.clear()

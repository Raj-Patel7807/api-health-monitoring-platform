"""Unit tests for Incidents API router (US-10 / Task B4).

Tests cover:
- GET /api/v1/incidents listing with pagination and filters
- GET /api/v1/incidents/{id} returning monitor_url and derived state
- Cross-team incident isolation (404 Not Found)
- Role permissions (admin, operator, read_only all have read access)
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.models import Team, TeamRole, User
from app.db.session import get_db
from app.main import app
from app.modules.incidents.schemas import (
    IncidentDetailResponse,
    IncidentResponse,
    IncidentStatus,
)
from app.modules.monitors.dependencies import (
    TeamContext,
    require_monitor_read,
)

_NOW = datetime.now(UTC)


@pytest.fixture()
def mock_team_context() -> TeamContext:
    user = User(id=uuid4(), email="user@example.com", full_name="Test User", password_hash="h")
    team = Team(id=uuid4(), name="Test Team")
    return TeamContext(user=user, team=team, role=TeamRole.read_only)


@pytest.fixture(autouse=True)
def _cleanup_overrides() -> None:
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_incidents_success(mock_team_context: TeamContext) -> None:
    """AC: GET /incidents supports status, monitor_id, pagination, newest first."""
    app.dependency_overrides[require_monitor_read] = lambda: mock_team_context
    app.dependency_overrides[get_db] = lambda: AsyncMock()

    dummy_incident = IncidentResponse(
        id=uuid4(),
        monitor_id=uuid4(),
        status=IncidentStatus.OPEN,
        opened_at=_NOW,
        resolved_at=None,
        failure_count=3,
        recovery_count=1,
        state="recovering",
    )

    with patch(
        "app.modules.incidents.service.list_incidents",
        new=AsyncMock(return_value=([dummy_incident], 1)),
    ) as mock_list:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/incidents?page=1&page_size=20&status=open")
            assert resp.status_code == 200
            data = resp.json()
            assert data["page"] == 1
            assert data["page_size"] == 20
            assert data["total"] == 1
            assert len(data["items"]) == 1
            item = data["items"][0]
            assert item["id"] == str(dummy_incident.id)
            assert item["status"] == "open"
            assert item["state"] == "recovering"
            assert item["failure_count"] == 3
            assert item["recovery_count"] == 1

            mock_list.assert_called_once()
            call_kwargs = mock_list.call_args.kwargs
            assert call_kwargs["team_id"] == mock_team_context.team.id
            assert call_kwargs["status_filter"] == IncidentStatus.OPEN
            assert call_kwargs["page"] == 1
            assert call_kwargs["page_size"] == 20


@pytest.mark.asyncio
async def test_get_incident_detail_success(mock_team_context: TeamContext) -> None:
    """AC: GET /incidents/{id} returns monitor_url."""
    app.dependency_overrides[require_monitor_read] = lambda: mock_team_context
    app.dependency_overrides[get_db] = lambda: AsyncMock()

    incident_id = uuid4()
    monitor_id = uuid4()
    dummy_detail = IncidentDetailResponse(
        id=incident_id,
        monitor_id=monitor_id,
        monitor_url="https://api.example.com/health",
        status=IncidentStatus.OPEN,
        opened_at=_NOW,
        resolved_at=None,
        failure_count=4,
        recovery_count=0,
        state="failing",
    )

    with patch(
        "app.modules.incidents.service.get_incident",
        new=AsyncMock(return_value=dummy_detail),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get(f"/api/v1/incidents/{incident_id}")
            assert resp.status_code == 200
            data = resp.json()
            assert data["id"] == str(incident_id)
            assert data["monitor_id"] == str(monitor_id)
            assert data["monitor_url"] == "https://api.example.com/health"
            assert data["status"] == "open"
            assert data["state"] == "failing"


@pytest.mark.asyncio
async def test_get_incident_detail_not_found_or_cross_team(
    mock_team_context: TeamContext,
) -> None:
    """AC: another team's incident returns 404."""
    app.dependency_overrides[require_monitor_read] = lambda: mock_team_context
    app.dependency_overrides[get_db] = lambda: AsyncMock()

    # Service returns None when the incident belongs to another team or does not exist
    with patch(
        "app.modules.incidents.service.get_incident",
        new=AsyncMock(return_value=None),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get(f"/api/v1/incidents/{uuid4()}")
            assert resp.status_code == 404
            assert resp.json()["detail"] == "Incident not found."


@pytest.mark.asyncio
@pytest.mark.parametrize("role", [TeamRole.admin, TeamRole.operator, TeamRole.read_only])
async def test_all_roles_have_read_access_to_incidents(role: TeamRole) -> None:
    """All team roles can view incidents."""
    user = User(id=uuid4(), email="u@test.com", full_name="User", password_hash="h")
    team = Team(id=uuid4(), name="Team")
    ctx = TeamContext(user=user, team=team, role=role)

    app.dependency_overrides[require_monitor_read] = lambda: ctx
    app.dependency_overrides[get_db] = lambda: AsyncMock()

    with patch(
        "app.modules.incidents.service.list_incidents",
        new=AsyncMock(return_value=([], 0)),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/incidents")
            assert resp.status_code == 200


@pytest.mark.asyncio
async def test_list_incidents_validation_errors(mock_team_context: TeamContext) -> None:
    """Boundary & input validation test: invalid query parameters return 422."""
    app.dependency_overrides[require_monitor_read] = lambda: mock_team_context
    app.dependency_overrides[get_db] = lambda: AsyncMock()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Invalid page (less than 1)
        resp1 = await ac.get("/api/v1/incidents?page=0")
        assert resp1.status_code == 422

        # Invalid page_size (0)
        resp2 = await ac.get("/api/v1/incidents?page_size=0")
        assert resp2.status_code == 422

        # Invalid page_size (exceeds max 100)
        resp3 = await ac.get("/api/v1/incidents?page_size=101")
        assert resp3.status_code == 422

        # Invalid status enum
        resp4 = await ac.get("/api/v1/incidents?status=not_a_valid_status")
        assert resp4.status_code == 422

        # Invalid monitor_id UUID format
        resp5 = await ac.get("/api/v1/incidents?monitor_id=not-a-uuid")
        assert resp5.status_code == 422


@pytest.mark.asyncio
async def test_get_incident_invalid_uuid(mock_team_context: TeamContext) -> None:
    """Invalid incident UUID format returns 422."""
    app.dependency_overrides[require_monitor_read] = lambda: mock_team_context
    app.dependency_overrides[get_db] = lambda: AsyncMock()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/v1/incidents/not-a-uuid")
        assert resp.status_code == 422

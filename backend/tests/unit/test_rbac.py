"""Parametrized RBAC tests for US-19.

This module implements the automated RBAC verification required by US-19:
1. ``test_all_routes_have_role_requirement`` — parametrized over all registered
   routes of the FastAPI application; fails if any route other than the public
   allowlist (signup, login, refresh, health, docs) lacks a role requirement.
2. ``test_role_matrix`` — parametrized over all (method, path, role) triples
   from the API.md RBAC matrix; asserts expected status code and verifies that
   403 responses return {"detail": "..."}.
3. ``test_auth_me_returns_team_id_name_role`` — asserts that GET /auth/me returns
   team.id, team.name, and team.role for the authenticated user.
4. ``test_cross_team_resource_returns_404_never_403`` — asserts that accessing
   resources belonging to another team returns 404, never 403.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.routing import APIRoute
from httpx import ASGITransport, AsyncClient

from app.core import config as cfg
from app.core.crypto import generate_key
from app.db.models import Team, TeamRole, User
from app.db.session import get_db
from app.main import app
from app.modules.channels.models import NotificationChannel
from app.modules.incidents.schemas import IncidentDetailResponse, IncidentStatus
from app.modules.monitors.dependencies import TeamContext, get_team_context
from app.modules.monitors.models import Monitor

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Public endpoints that intentionally carry no RBAC dependency.
_PUBLIC_PATHS: set[str] = {
    "/api/v1/auth/signup",
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
    "/api/v1/auth/me",
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/docs/oauth2-redirect",
    # Test harness endpoints for local webhook/email development (PR #52)
    "/deliveries/",
    "/deliveries/{delivery_id}",
    "/deliveries/{delivery_id}/replay",
    "/harness/email",
    "/harness/webhook",
}

# Shared dummy IDs used in parametrized path templates.
_MONITOR_ID = uuid4()
_CHANNEL_ID = uuid4()
_INCIDENT_ID = uuid4()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_context(role: TeamRole) -> TeamContext:
    user = User(
        id=uuid4(),
        email=f"{role.value}@test.com",
        full_name=role.value,
        password_hash="h",
    )
    team = Team(id=uuid4(), name="Test Team")
    return TeamContext(user=user, team=team, role=role)


def _get_all_routes() -> list[APIRoute]:
    routes: list[APIRoute] = []

    def _collect(router_or_app: Any) -> None:
        for r in getattr(router_or_app, "routes", []):
            if isinstance(r, APIRoute):
                routes.append(r)
            elif hasattr(r, "original_router"):
                _collect(r.original_router)
            elif hasattr(r, "router"):
                _collect(r.router)

    _collect(app)
    return routes


def _dep_names(route: APIRoute) -> set[str]:
    """Return the set of all dependency callable names reachable from a route."""
    names: set[str] = set()

    def _walk(dependant: Any) -> None:  # noqa: ANN401
        if dependant is None:
            return
        if getattr(dependant, "call", None):
            names.add(getattr(dependant.call, "__name__", repr(dependant.call)))
        for sub in getattr(dependant, "dependencies", []):
            _walk(sub)

    _walk(route.dependant)
    return names


# ---------------------------------------------------------------------------
# Test 1 — Every non-public route has a role requirement (parametrized)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "route",
    _get_all_routes(),
    ids=lambda r: f"{list(r.methods)} {r.path}",
)
def test_all_routes_have_role_requirement(route: APIRoute) -> None:
    """Every protected route must have get_team_context reachable in its dependency tree."""
    if route.path in _PUBLIC_PATHS:
        return

    dep_names = _dep_names(route)
    assert "get_team_context" in dep_names, (
        f"Route {list(route.methods)} {route.path} has no role requirement! "
        "Every protected route must enforce team context and role checks."
    )


# ---------------------------------------------------------------------------
# Test 2 — Full RBAC Matrix: Expected status per route per role
# ---------------------------------------------------------------------------

# Format: (method, path_template, role, expected_status, body_or_None)
_MATRIX: list[tuple[str, str, TeamRole, int, dict[str, Any] | None]] = [
    # --- Monitors: GET list (all roles can view) ---
    ("GET", "/api/v1/monitors", TeamRole.admin, 200, None),
    ("GET", "/api/v1/monitors", TeamRole.operator, 200, None),
    ("GET", "/api/v1/monitors", TeamRole.read_only, 200, None),
    # --- Monitors: POST (admin + operator only; read_only 403) ---
    ("POST", "/api/v1/monitors", TeamRole.admin, 201, {"name": "M", "url": "https://example.com"}),
    (
        "POST",
        "/api/v1/monitors",
        TeamRole.operator,
        201,
        {"name": "M", "url": "https://example.com"},
    ),
    (
        "POST",
        "/api/v1/monitors",
        TeamRole.read_only,
        403,
        {"name": "M", "url": "https://example.com"},
    ),
    # --- Monitors: GET detail (all roles can view) ---
    ("GET", "/api/v1/monitors/{monitor_id}", TeamRole.admin, 200, None),
    ("GET", "/api/v1/monitors/{monitor_id}", TeamRole.operator, 200, None),
    ("GET", "/api/v1/monitors/{monitor_id}", TeamRole.read_only, 200, None),
    # --- Monitors: PATCH (admin + operator only; read_only 403) ---
    ("PATCH", "/api/v1/monitors/{monitor_id}", TeamRole.admin, 200, {"name": "X"}),
    ("PATCH", "/api/v1/monitors/{monitor_id}", TeamRole.operator, 200, {"name": "X"}),
    ("PATCH", "/api/v1/monitors/{monitor_id}", TeamRole.read_only, 403, {"name": "X"}),
    # --- Monitors: DELETE (admin only; operator 403, read_only 403) ---
    ("DELETE", "/api/v1/monitors/{monitor_id}", TeamRole.admin, 204, None),
    ("DELETE", "/api/v1/monitors/{monitor_id}", TeamRole.operator, 403, None),
    ("DELETE", "/api/v1/monitors/{monitor_id}", TeamRole.read_only, 403, None),
    # --- Results: GET (all roles can view) ---
    ("GET", "/api/v1/monitors/{monitor_id}/results", TeamRole.admin, 200, None),
    ("GET", "/api/v1/monitors/{monitor_id}/results", TeamRole.operator, 200, None),
    ("GET", "/api/v1/monitors/{monitor_id}/results", TeamRole.read_only, 200, None),
    # --- Channels: GET list (admin + operator; read_only 403, even to view) ---
    ("GET", "/api/v1/notification-channels", TeamRole.admin, 200, None),
    ("GET", "/api/v1/notification-channels", TeamRole.operator, 200, None),
    ("GET", "/api/v1/notification-channels", TeamRole.read_only, 403, None),
    # --- Channels: POST (admin + operator; read_only 403) ---
    (
        "POST",
        "/api/v1/notification-channels",
        TeamRole.admin,
        201,
        {"type": "slack", "name": "C", "secret_value": "https://hooks.slack.com/services/T/B/X"},
    ),
    (
        "POST",
        "/api/v1/notification-channels",
        TeamRole.operator,
        201,
        {"type": "slack", "name": "C", "secret_value": "https://hooks.slack.com/services/T/B/X"},
    ),
    (
        "POST",
        "/api/v1/notification-channels",
        TeamRole.read_only,
        403,
        {"type": "slack", "name": "C", "secret_value": "https://hooks.slack.com/services/T/B/X"},
    ),
    # --- Channels: PATCH (admin + operator; read_only 403) ---
    ("PATCH", "/api/v1/notification-channels/{channel_id}", TeamRole.admin, 200, {"name": "Y"}),
    ("PATCH", "/api/v1/notification-channels/{channel_id}", TeamRole.operator, 200, {"name": "Y"}),
    ("PATCH", "/api/v1/notification-channels/{channel_id}", TeamRole.read_only, 403, {"name": "Y"}),
    # --- Channels: DELETE (admin + operator; read_only 403) ---
    ("DELETE", "/api/v1/notification-channels/{channel_id}", TeamRole.admin, 204, None),
    ("DELETE", "/api/v1/notification-channels/{channel_id}", TeamRole.operator, 204, None),
    ("DELETE", "/api/v1/notification-channels/{channel_id}", TeamRole.read_only, 403, None),
    # --- Incidents: GET list (all roles can view) ---
    ("GET", "/api/v1/incidents", TeamRole.admin, 200, None),
    ("GET", "/api/v1/incidents", TeamRole.operator, 200, None),
    ("GET", "/api/v1/incidents", TeamRole.read_only, 200, None),
    # --- Incidents: GET detail (all roles can view) ---
    ("GET", "/api/v1/incidents/{incident_id}", TeamRole.admin, 200, None),
    ("GET", "/api/v1/incidents/{incident_id}", TeamRole.operator, 200, None),
    ("GET", "/api/v1/incidents/{incident_id}", TeamRole.read_only, 200, None),
    # --- Alert deliveries: GET (all roles can view) ---
    ("GET", "/api/v1/incidents/{incident_id}/alert-deliveries", TeamRole.admin, 200, None),
    ("GET", "/api/v1/incidents/{incident_id}/alert-deliveries", TeamRole.operator, 200, None),
    ("GET", "/api/v1/incidents/{incident_id}/alert-deliveries", TeamRole.read_only, 200, None),
]


def _resolve_path(template: str) -> str:
    return (
        template.replace("{monitor_id}", str(_MONITOR_ID))
        .replace("{channel_id}", str(_CHANNEL_ID))
        .replace("{incident_id}", str(_INCIDENT_ID))
    )


def _make_id(method: str, path: str, role: TeamRole) -> str:
    short = path.replace("/api/v1/", "").replace("/", "_")
    return f"{method.lower()}_{short}_{role.value}"


@pytest.mark.parametrize(
    "method,path_tmpl,role,expected_status,body",
    _MATRIX,
    ids=[_make_id(m, p, r) for m, p, r, _, _ in _MATRIX],
)
@pytest.mark.asyncio
async def test_role_matrix(
    method: str,
    path_tmpl: str,
    role: TeamRole,
    expected_status: int,
    body: dict[str, Any] | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Assert every (method, endpoint, role) combination returns the expected status."""
    _test_key = generate_key()
    monkeypatch.setenv("ENCRYPTION_KEY", _test_key)
    cfg.get_settings.cache_clear()

    ctx = _make_context(role)
    path = _resolve_path(path_tmpl)

    monitor_obj = _make_dummy_monitor(ctx.team.id)
    channel_obj = _make_dummy_channel(ctx.team.id)
    incident_obj = _make_dummy_incident(ctx.team.id, monitor_obj.id)

    app.dependency_overrides[get_team_context] = lambda: ctx
    app.dependency_overrides[get_db] = lambda: AsyncMock()

    now = datetime.now(UTC)

    with (
        patch(
            "app.modules.monitors.service.list_monitors",
            new=AsyncMock(return_value=([], 0)),
        ),
        patch(
            "app.modules.monitors.service.get_monitor",
            new=AsyncMock(return_value=monitor_obj),
        ),
        patch(
            "app.modules.monitors.service.create_monitor",
            new=AsyncMock(return_value=monitor_obj),
        ),
        patch(
            "app.modules.monitors.service.update_monitor",
            new=AsyncMock(return_value=monitor_obj),
        ),
        patch(
            "app.modules.monitors.service.soft_delete_monitor",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "app.modules.monitors.router.results_service.list_health_check_results",
            new=AsyncMock(return_value=([], 0, now, now)),
        ),
        patch(
            "app.modules.channels.service.list_channels",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.modules.channels.service.create_channel",
            new=AsyncMock(return_value=channel_obj),
        ),
        patch(
            "app.modules.channels.service.get_channel",
            new=AsyncMock(return_value=channel_obj),
        ),
        patch(
            "app.modules.channels.service.update_channel",
            new=AsyncMock(return_value=channel_obj),
        ),
        patch(
            "app.modules.channels.service.soft_delete_channel",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "app.modules.incidents.service.list_incidents",
            new=AsyncMock(return_value=([], 0)),
        ),
        patch(
            "app.modules.incidents.service.get_incident",
            new=AsyncMock(return_value=incident_obj),
        ),
    ):
        if "alert-deliveries" in path:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                mock_db = AsyncMock()
                mock_inc_result = MagicMock()
                mock_inc_result.scalar_one_or_none.return_value = object()
                mock_del_result = MagicMock()
                mock_del_result.all.return_value = []
                mock_db.execute.side_effect = [mock_inc_result, mock_del_result]
                app.dependency_overrides[get_db] = lambda: mock_db

                resp = await ac.request(method, path, json=body)
        else:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.request(method, path, json=body)

    app.dependency_overrides.clear()
    cfg.get_settings.cache_clear()

    assert resp.status_code == expected_status, (
        f"{method} {path} as {role.value}: expected {expected_status}, got {resp.status_code}. "
        f"Body: {resp.text[:300]}"
    )

    if expected_status == 403:
        data = resp.json()
        assert "detail" in data, f"403 response body must contain 'detail': {data}"
        assert isinstance(data["detail"], str), "'detail' in 403 must be a string."


# ---------------------------------------------------------------------------
# Test 3 — GET /auth/me returns team.id, team.name and team.role (US-19 AC)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auth_me_returns_team_id_name_role() -> None:
    """GET /auth/me must return team: { id, name, role } for the caller."""
    from app.auth.dependencies import get_current_user

    user_id = uuid4()
    team_id = uuid4()

    user = User(
        id=user_id,
        email="testme@example.com",
        full_name="Test Me",
        password_hash="h",
        is_active=True,
        created_at=datetime.now(UTC),
    )
    team = Team(id=team_id, name="Engineers")

    membership = MagicMock()
    membership.role = TeamRole.operator

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.first.return_value = (membership, team)
    mock_db.execute.return_value = mock_result

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: mock_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/v1/auth/me")

    app.dependency_overrides.clear()

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(user_id)
    assert data["email"] == "testme@example.com"
    assert "team" in data
    assert data["team"] is not None
    assert data["team"]["id"] == str(team_id)
    assert data["team"]["name"] == "Engineers"
    assert data["team"]["role"] == "operator"


# ---------------------------------------------------------------------------
# Test 4 — Resource from another team returns 404, never 403 (US-19 AC)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "method,path_tmpl,role",
    [
        ("GET", "/api/v1/monitors/{monitor_id}", TeamRole.admin),
        ("GET", "/api/v1/monitors/{monitor_id}", TeamRole.operator),
        ("GET", "/api/v1/monitors/{monitor_id}", TeamRole.read_only),
        ("PATCH", "/api/v1/monitors/{monitor_id}", TeamRole.admin),
        ("PATCH", "/api/v1/monitors/{monitor_id}", TeamRole.operator),
        ("DELETE", "/api/v1/monitors/{monitor_id}", TeamRole.admin),
        ("GET", "/api/v1/monitors/{monitor_id}/results", TeamRole.admin),
        ("GET", "/api/v1/monitors/{monitor_id}/results", TeamRole.operator),
        ("GET", "/api/v1/monitors/{monitor_id}/results", TeamRole.read_only),
        ("PATCH", "/api/v1/notification-channels/{channel_id}", TeamRole.admin),
        ("PATCH", "/api/v1/notification-channels/{channel_id}", TeamRole.operator),
        ("DELETE", "/api/v1/notification-channels/{channel_id}", TeamRole.admin),
        ("DELETE", "/api/v1/notification-channels/{channel_id}", TeamRole.operator),
        ("GET", "/api/v1/incidents/{incident_id}", TeamRole.admin),
        ("GET", "/api/v1/incidents/{incident_id}", TeamRole.operator),
        ("GET", "/api/v1/incidents/{incident_id}", TeamRole.read_only),
        ("GET", "/api/v1/incidents/{incident_id}/alert-deliveries", TeamRole.admin),
        ("GET", "/api/v1/incidents/{incident_id}/alert-deliveries", TeamRole.operator),
        ("GET", "/api/v1/incidents/{incident_id}/alert-deliveries", TeamRole.read_only),
    ],
)
@pytest.mark.asyncio
async def test_cross_team_resource_returns_404_never_403(
    method: str,
    path_tmpl: str,
    role: TeamRole,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When a resource does not belong to the caller's team, return 404, never 403."""
    _test_key = generate_key()
    monkeypatch.setenv("ENCRYPTION_KEY", _test_key)
    cfg.get_settings.cache_clear()

    ctx = _make_context(role)
    path = _resolve_path(path_tmpl)

    app.dependency_overrides[get_team_context] = lambda: ctx
    app.dependency_overrides[get_db] = lambda: AsyncMock()

    # All service lookups return None (resource not found in this team)
    with (
        patch("app.modules.monitors.service.get_monitor", new=AsyncMock(return_value=None)),
        patch("app.modules.channels.service.get_channel", new=AsyncMock(return_value=None)),
        patch("app.modules.incidents.service.get_incident", new=AsyncMock(return_value=None)),
    ):
        if "alert-deliveries" in path:
            mock_db = AsyncMock()
            mock_inc_result = MagicMock()
            mock_inc_result.scalar_one_or_none.return_value = None  # Not found in this team
            mock_db.execute.return_value = mock_inc_result
            app.dependency_overrides[get_db] = lambda: mock_db

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.request(method, path)
        else:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                body = {"name": "updated"} if method == "PATCH" else None
                resp = await ac.request(method, path, json=body)

    app.dependency_overrides.clear()
    cfg.get_settings.cache_clear()

    assert resp.status_code == 404, (
        f"Cross-team access {method} {path} as {role.value} returned {resp.status_code}, "
        "expected 404 Not Found to prevent leaking resource existence across teams."
    )


# ---------------------------------------------------------------------------
# Dummy model factories
# ---------------------------------------------------------------------------


def _make_dummy_monitor(team_id: Any = None) -> Monitor:
    now = datetime.now(UTC)
    return Monitor(
        id=_MONITOR_ID,
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
        next_check_at=now,
        created_at=now,
        updated_at=now,
    )


def _make_dummy_channel(team_id: Any = None) -> NotificationChannel:
    now = datetime.now(UTC)
    return NotificationChannel(
        id=_CHANNEL_ID,
        team_id=team_id or uuid4(),
        monitor_id=None,
        type="slack",
        name="Test Channel",
        is_enabled=True,
        configuration="{}",
        secret_ref="encrypted-blob",
        secret_display_hint="hooks.slack.com/…/X",
        created_at=now,
        updated_at=now,
    )


def _make_dummy_incident(team_id: Any, monitor_id: Any) -> IncidentDetailResponse:
    now = datetime.now(UTC)
    return IncidentDetailResponse(
        id=_INCIDENT_ID,
        monitor_id=monitor_id,
        monitor_url="https://api.example.com",
        status=IncidentStatus.OPEN,
        opened_at=now,
        resolved_at=None,
        failure_count=3,
        recovery_count=0,
        state="open",
    )

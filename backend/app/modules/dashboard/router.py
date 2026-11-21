"""FastAPI router for Dashboard (US-13).

Endpoints:
----------
GET /api/v1/dashboard   Retrieve overall health dashboard for the caller's team.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TeamRole
from app.db.session import get_db
from app.modules.dashboard.schemas import DashboardResponse
from app.modules.dashboard.service import get_dashboard
from app.modules.monitors.dependencies import (
    TeamContext,
    require_roles,
)

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])

_require_dashboard_access = require_roles({TeamRole.admin, TeamRole.operator, TeamRole.read_only})


@router.get("", response_model=DashboardResponse)
async def read_dashboard(
    context: Annotated[TeamContext, Depends(_require_dashboard_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DashboardResponse:
    """Return consolidated health metrics for all active monitors belonging to the caller's team."""
    return await get_dashboard(db=db, team_id=context.team.id)

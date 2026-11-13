"""FastAPI router for Incidents (US-10 / Task B4).

Endpoints:
----------
GET /api/v1/incidents        List incidents for the caller's team with pagination and filters.
GET /api/v1/incidents/{id}   Get incident detail including monitor_url (scoped to team).
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.incidents import service
from app.modules.incidents.schemas import (
    IncidentDetailResponse,
    IncidentListResponse,
    IncidentStatus,
)
from app.modules.monitors.dependencies import (
    TeamContext,
    require_monitor_read,
)

router = APIRouter(prefix="/api/v1/incidents", tags=["incidents"])


@router.get("", response_model=IncidentListResponse)
async def list_incidents(
    context: Annotated[TeamContext, Depends(require_monitor_read)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: Annotated[
        IncidentStatus | None,
        Query(alias="status", description="Filter by status (open, resolved)"),
    ] = None,
    monitor_id: Annotated[
        UUID | None,
        Query(description="Filter by monitor ID"),
    ] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
) -> IncidentListResponse:
    """List incidents for monitors belonging to the caller's team."""
    items, total = await service.list_incidents(
        db=db,
        team_id=context.team.id,
        status_filter=status_filter,
        monitor_id=monitor_id,
        page=page,
        page_size=page_size,
    )
    return IncidentListResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/{id}", response_model=IncidentDetailResponse)
async def get_incident(
    id: UUID,
    context: Annotated[TeamContext, Depends(require_monitor_read)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> IncidentDetailResponse:
    """Retrieve details for a single incident including monitor_url.

    Returns 404 if the incident does not exist or belongs to another team's monitor.
    """
    incident = await service.get_incident(
        db=db,
        team_id=context.team.id,
        incident_id=id,
    )
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found.",
        )
    return incident

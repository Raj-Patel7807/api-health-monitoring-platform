"""FastAPI router for Monitor CRUD (US-02).

Endpoints:
----------
POST   /api/v1/monitors        Create a new monitor under caller's team (admin/operator).
GET    /api/v1/monitors        List monitors for caller's team with pagination.
GET    /api/v1/monitors/{id}   Get monitor details by ID (scoped to team).
PATCH  /api/v1/monitors/{id}   Partially update monitor (admin/operator).
DELETE /api/v1/monitors/{id}   Soft delete monitor (admin/operator).
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TeamMembership, TeamRole
from app.db.session import get_db
from app.modules.monitors import service
from app.modules.monitors.dependencies import (
    TeamContext,
    require_monitor_read,
    require_monitor_write,
)
from app.modules.monitors.schemas import (
    MonitorCreateRequest,
    MonitorDetailResponse,
    MonitorListResponse,
    MonitorResponse,
    MonitorUpdateRequest,
)

router = APIRouter(prefix="/api/v1/monitors", tags=["monitors"])


@router.post(
    "",
    response_model=MonitorDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_monitor(
    body: MonitorCreateRequest,
    context: Annotated[TeamContext, Depends(require_monitor_write)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MonitorDetailResponse:
    """Register and configure a new API endpoint monitor under the active team."""
    effective_team_id = context.team.id
    if body.team_id is not None and body.team_id != context.team.id:
        # Cross-team creation requested: verify user is an admin or operator on target team
        stmt = select(TeamMembership).where(
            TeamMembership.team_id == body.team_id,
            TeamMembership.user_id == context.user.id,
            TeamMembership.role.in_([TeamRole.admin, TeamRole.operator]),
        )
        membership = (await db.execute(stmt)).scalar_one_or_none()
        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to create monitors for the specified team.",
            )
        effective_team_id = body.team_id

    monitor = await service.create_monitor(db, effective_team_id, body)
    return MonitorDetailResponse.model_validate(monitor)


@router.get("", response_model=MonitorListResponse)
async def list_monitors(
    context: Annotated[TeamContext, Depends(require_monitor_read)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
) -> MonitorListResponse:
    """List active monitors belonging to the caller's team."""
    items, total = await service.list_monitors(
        db=db,
        team_id=context.team.id,
        page=page,
        page_size=page_size,
    )
    return MonitorListResponse(
        items=[MonitorResponse.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/{id}", response_model=MonitorDetailResponse)
async def get_monitor(
    id: UUID,
    context: Annotated[TeamContext, Depends(require_monitor_read)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MonitorDetailResponse:
    """Retrieve full configuration and current health state for a single monitor."""
    monitor = await service.get_monitor(db, context.team.id, id)
    if monitor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitor not found.",
        )
    return MonitorDetailResponse.model_validate(monitor)


@router.patch("/{id}", response_model=MonitorDetailResponse)
async def update_monitor(
    id: UUID,
    body: MonitorUpdateRequest,
    context: Annotated[TeamContext, Depends(require_monitor_write)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MonitorDetailResponse:
    """Partially update an existing monitor."""
    monitor = await service.get_monitor(db, context.team.id, id)
    if monitor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitor not found.",
        )
    updated = await service.update_monitor(db, monitor, body)
    return MonitorDetailResponse.model_validate(updated)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_monitor(
    id: UUID,
    context: Annotated[TeamContext, Depends(require_monitor_write)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Soft delete a monitor by setting deleted_at and disabling it."""
    monitor = await service.get_monitor(db, context.team.id, id)
    if monitor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitor not found.",
        )
    await service.soft_delete_monitor(db, monitor)

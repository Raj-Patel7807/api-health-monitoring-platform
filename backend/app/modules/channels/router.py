"""FastAPI router for Notification Channel CRUD (US-03).

Endpoints:
----------
GET    /api/v1/notification-channels           List channels (admin/operator).
POST   /api/v1/notification-channels           Create a channel (admin/operator).
PATCH  /api/v1/notification-channels/{id}      Update name/enabled/secret (admin/operator).
DELETE /api/v1/notification-channels/{id}      Soft-delete (admin/operator).

read_only users receive 403 on all endpoints (see RBAC matrix in API.md).
type and monitor_id cannot be changed after creation — delete and recreate.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TeamRole
from app.db.session import get_db
from app.modules.channels import service
from app.modules.channels.schemas import (
    ChannelCreateRequest,
    ChannelListResponse,
    ChannelResponse,
    ChannelUpdateRequest,
)
from app.modules.monitors.dependencies import TeamContext, require_roles

router = APIRouter(prefix="/api/v1/notification-channels", tags=["channels"])

# admin and operator can manage channels; read_only cannot (RBAC matrix US-03)
_require_channel_access = require_roles({TeamRole.admin, TeamRole.operator})


@router.get("", response_model=ChannelListResponse)
async def list_channels(
    context: Annotated[TeamContext, Depends(_require_channel_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
    monitor_id: Annotated[UUID | None, Query(description="Filter by monitor")] = None,
    scope: Annotated[
        str | None, Query(description="'team' returns only team-wide channels")
    ] = None,
) -> ChannelListResponse:
    """List active notification channels for the caller's team."""
    scope_team_only = scope == "team"
    items = await service.list_channels(
        db,
        team_id=context.team.id,
        monitor_id=monitor_id,
        scope_team_only=scope_team_only,
    )
    return ChannelListResponse(items=[ChannelResponse.model_validate(ch) for ch in items])


@router.post("", response_model=ChannelResponse, status_code=status.HTTP_201_CREATED)
async def create_channel(
    body: ChannelCreateRequest,
    context: Annotated[TeamContext, Depends(_require_channel_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ChannelResponse:
    """Create a notification channel.  The secret is validated then discarded."""
    if body.monitor_id is not None:
        # Verify the monitor exists and belongs to this team.
        from app.modules.monitors import service as mon_service

        monitor = await mon_service.get_monitor(db, context.team.id, body.monitor_id)
        if monitor is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Monitor not found.",
            )

    channel = await service.create_channel(db, context.team.id, body)
    return ChannelResponse.model_validate(channel)


@router.patch("/{id}", response_model=ChannelResponse)
async def update_channel(
    id: UUID,
    body: ChannelUpdateRequest,
    context: Annotated[TeamContext, Depends(_require_channel_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ChannelResponse:
    """Update name, enabled state, or rotate secret.

    type and monitor_id cannot change — delete and recreate instead.
    Omitting secret_value keeps the current secret unchanged.
    """
    channel = await service.get_channel(db, context.team.id, id)
    if channel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification channel not found.",
        )

    if body.secret_value is not None:
        # Re-validate the new secret against the channel's existing type
        from app.modules.channels.models import ChannelType
        from app.modules.channels.schemas import _validate_secret

        _validate_secret(ChannelType(channel.type), body.secret_value)

    updated = await service.update_channel(db, channel, body, channel.type)
    return ChannelResponse.model_validate(updated)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_channel(
    id: UUID,
    context: Annotated[TeamContext, Depends(_require_channel_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Soft-delete a notification channel (sets deleted_at, hides from lists)."""
    channel = await service.get_channel(db, context.team.id, id)
    if channel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification channel not found.",
        )
    await service.soft_delete_channel(db, channel)

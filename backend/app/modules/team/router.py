"""FastAPI router for Team Members (US-19).

Endpoints:
----------
GET   /api/v1/team/members          List members of the caller's team (admin, operator).
POST  /api/v1/team/members          Attach existing user to the team (admin only).
PATCH /api/v1/team/members/{user_id} Change role of a team member (admin only).
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TeamRole
from app.db.session import get_db
from app.modules.monitors.dependencies import (
    TeamContext,
    require_roles,
)
from app.modules.team import service
from app.modules.team.schemas import (
    AddTeamMemberRequest,
    TeamMemberListResponse,
    TeamMemberResponse,
    UpdateTeamMemberRoleRequest,
)

router = APIRouter(prefix="/api/v1/team", tags=["team"])

_require_member_read = require_roles({TeamRole.admin, TeamRole.operator})
_require_member_admin = require_roles({TeamRole.admin})


@router.get("/members", response_model=TeamMemberListResponse)
async def list_members(
    context: Annotated[TeamContext, Depends(_require_member_read)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TeamMemberListResponse:
    """List members belonging to the caller's team.

    Accessible to admin and operator roles; returns 403 for read_only.
    """
    members = await service.list_team_members(db=db, team_id=context.team.id)
    return TeamMemberListResponse(items=members)


@router.post(
    "/members",
    response_model=TeamMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_member(
    body: AddTeamMemberRequest,
    context: Annotated[TeamContext, Depends(_require_member_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TeamMemberResponse:
    """Attach an existing user to the caller's team with a designated role.

    Admin-only. Returns 404 if email is unknown, and 409 if already a member.
    """
    return await service.add_team_member(
        db=db,
        team_id=context.team.id,
        email=body.email,
        role=body.role,
    )


@router.patch("/members/{user_id}", response_model=TeamMemberResponse)
async def update_member_role(
    user_id: UUID,
    body: UpdateTeamMemberRoleRequest,
    context: Annotated[TeamContext, Depends(_require_member_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TeamMemberResponse:
    """Update the role of a member belonging to the caller's team.

    Admin-only. Returns 409 if the operation would demote the team's last admin.
    """
    return await service.update_team_member_role(
        db=db,
        team_id=context.team.id,
        user_id=user_id,
        new_role=body.role,
    )

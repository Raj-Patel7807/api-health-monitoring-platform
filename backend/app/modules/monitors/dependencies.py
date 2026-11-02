"""Dependencies for team scoping and RBAC authorization on monitors."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.models import Team, TeamMembership, TeamRole, User
from app.db.session import get_db


@dataclass
class TeamContext:
    user: User
    team: Team
    role: TeamRole


async def get_team_context(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    x_team_id: Annotated[UUID | None, Header(alias="X-Team-ID")] = None,
    team_id: Annotated[UUID | None, Query(description="Target team ID")] = None,
) -> TeamContext:
    """Resolve the active team context and membership role for the authenticated user.

    Supports explicit team selection via X-Team-ID header or team_id query parameter,
    defaulting to the user's primary/first active team membership.
    """
    target_team_id = x_team_id or team_id

    stmt = (
        select(TeamMembership, Team)
        .join(Team, TeamMembership.team_id == Team.id)
        .where(
            TeamMembership.user_id == current_user.id,
            Team.deleted_at.is_(None),
        )
    )

    if target_team_id is not None:
        stmt = stmt.where(TeamMembership.team_id == target_team_id)

    stmt = stmt.order_by(TeamMembership.created_at.asc())
    result = await db.execute(stmt)
    row = result.first()

    if row is None:
        if target_team_id is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access the requested team.",
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not belong to any active team.",
        )

    membership, team = row
    return TeamContext(user=current_user, team=team, role=membership.role)


def require_roles(allowed_roles: set[TeamRole]) -> Callable[..., TeamContext]:
    """Dependency factory checking that the caller's team role is in allowed_roles."""

    def _role_checker(
        context: Annotated[TeamContext, Depends(get_team_context)],
    ) -> TeamContext:
        if context.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{context.role.value}' does not have permission for this action.",
            )
        return context

    return _role_checker


require_monitor_read = require_roles({TeamRole.admin, TeamRole.operator, TeamRole.read_only})
require_monitor_write = require_roles({TeamRole.admin, TeamRole.operator})

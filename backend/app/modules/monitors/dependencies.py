"""Dependencies for team scoping and RBAC authorization on monitors.

Team resolution rule (Sprint 4, day-1 decision 1)
-------------------------------------------------
A user's **active team** is the team they joined most recently, resolved by
ordering ``TeamMembership.created_at`` descending and taking the first row.
Signup creates exactly one team per user, so for most users this is their only
team.  When a user is later added to a second team, that newer membership
becomes the active one.  Callers may override via the ``X-Team-ID`` header or
``team_id`` query parameter to address a specific team by UUID.

See also: docs/design/API.md § "Active team (Sprint 4 decision)".
"""

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

    Active team = most recently joined team (``created_at`` DESC).  Callers
    may pin a specific team via the ``X-Team-ID`` header or ``team_id`` query
    parameter.
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

    # Most recently joined team is the active one (Sprint 4 day-1 decision 1).
    stmt = stmt.order_by(TeamMembership.created_at.desc())
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


def require_role(*allowed_roles: TeamRole) -> Callable[..., TeamContext]:
    """Dependency factory checking that the caller's team role is in allowed_roles."""
    return require_roles(set(allowed_roles))


# ---------------------------------------------------------------------------
# Named dependency aliases (use these in routers, not raw require_roles calls)
# ---------------------------------------------------------------------------

#: Any authenticated team member (admin, operator, read_only).
require_monitor_read = require_roles({TeamRole.admin, TeamRole.operator, TeamRole.read_only})

#: Admin or operator — can create and edit resources.
require_monitor_write = require_roles({TeamRole.admin, TeamRole.operator})

#: Admin only — destructive or privileged operations (e.g. deleting a monitor).
require_admin = require_roles({TeamRole.admin})

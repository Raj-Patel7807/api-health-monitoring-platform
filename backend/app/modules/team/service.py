"""Team member management service layer (US-19).

Handles listing team members, attaching existing users to a team, and
updating member roles with last-admin demotion protection.
"""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TeamMembership, TeamRole, User
from app.modules.team.schemas import TeamMemberResponse


async def list_team_members(
    db: AsyncSession,
    team_id: UUID,
) -> list[TeamMemberResponse]:
    """Return all members belonging to the specified team."""
    stmt = (
        select(User.id, User.email, User.full_name, TeamMembership.role)
        .join(TeamMembership, TeamMembership.user_id == User.id)
        .where(TeamMembership.team_id == team_id)
        .order_by(TeamMembership.created_at.asc(), User.full_name.asc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    return [
        TeamMemberResponse(
            user_id=row.id,
            email=row.email,
            full_name=row.full_name,
            role=row.role,
        )
        for row in rows
    ]


async def add_team_member(
    db: AsyncSession,
    team_id: UUID,
    email: str,
    role: TeamRole,
) -> TeamMemberResponse:
    """Attach an existing user to the team with the requested role.

    Raises:
        HTTPException 404: If no user exists with the specified email.
        HTTPException 409: If the user is already a member of the team.
    """
    normalized_email = email.strip().lower()
    user_stmt = select(User).where(func.lower(User.email) == normalized_email)
    user = (await db.execute(user_stmt)).scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found with the provided email address.",
        )

    membership_stmt = select(TeamMembership).where(
        TeamMembership.team_id == team_id,
        TeamMembership.user_id == user.id,
    )
    existing_membership = (await db.execute(membership_stmt)).scalar_one_or_none()

    if existing_membership is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member of this team.",
        )

    membership = TeamMembership(
        team_id=team_id,
        user_id=user.id,
        role=role,
    )
    db.add(membership)
    await db.commit()

    return TeamMemberResponse(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=membership.role,
    )


async def update_team_member_role(
    db: AsyncSession,
    team_id: UUID,
    user_id: UUID,
    new_role: TeamRole,
) -> TeamMemberResponse:
    """Change the role of an existing team member.

    Raises:
        HTTPException 404: If the target user is not a member of this team.
        HTTPException 409: If demoting the user would leave the team with 0 admins.
    """
    stmt = (
        select(TeamMembership)
        .where(
            TeamMembership.team_id == team_id,
            TeamMembership.user_id == user_id,
        )
        .with_for_update()
    )
    membership = (await db.execute(stmt)).scalar_one_or_none()

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team member not found.",
        )

    if membership.role == TeamRole.admin and new_role != TeamRole.admin:
        admin_count_stmt = (
            select(func.count())
            .select_from(TeamMembership)
            .where(
                TeamMembership.team_id == team_id,
                TeamMembership.role == TeamRole.admin,
            )
        )
        admin_count = (await db.execute(admin_count_stmt)).scalar() or 0
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot demote the last remaining admin of the team.",
            )

    membership.role = new_role
    await db.commit()

    user_stmt = select(User).where(User.id == user_id)
    user = (await db.execute(user_stmt)).scalar_one()

    return TeamMemberResponse(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=membership.role,
    )

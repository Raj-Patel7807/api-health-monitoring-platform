"""Pydantic schemas for Team Members management (US-19)."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

from app.db.models import TeamRole


class TeamMemberResponse(BaseModel):
    """Details of a single team member."""

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    email: str
    full_name: str
    role: TeamRole


class TeamMemberListResponse(BaseModel):
    """List of all members in the caller's team."""

    model_config = ConfigDict(from_attributes=True)

    items: list[TeamMemberResponse]


class AddTeamMemberRequest(BaseModel):
    """Request payload to attach an existing user to the team."""

    email: EmailStr
    role: TeamRole


class UpdateTeamMemberRoleRequest(BaseModel):
    """Request payload to update the role of an existing team member."""

    role: TeamRole

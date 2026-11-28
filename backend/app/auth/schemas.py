"""Pydantic v2 request and response schemas for the auth endpoints."""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.db.models import TeamRole

# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


class SignupRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=150)
    password: str = Field(min_length=8, max_length=128)
    team_name: str | None = Field(default=None, min_length=1, max_length=150)

    @field_validator("password")
    @classmethod
    def password_not_email(cls, v: str, info: object) -> str:
        # Cheap sanity check — email is validated separately.
        if len(v.strip()) == 0:
            raise ValueError("password must not be blank")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str


class UpdateMeRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=150)
    email: EmailStr | None = None
    current_password: str | None = Field(default=None, min_length=1, max_length=128)
    new_password: str | None = Field(default=None, min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def new_password_not_blank(cls, v: str | None) -> str | None:
        if v is not None and len(v.strip()) == 0:
            raise ValueError("password must not be blank")
        return v


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TeamInResponse(BaseModel):
    """Minimal team representation embedded in the /auth/me response (US-19)."""

    id: uuid.UUID
    name: str
    role: TeamRole

    model_config = {"from_attributes": True}


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    is_active: bool
    created_at: datetime
    team: TeamInResponse | None = None

    model_config = {"from_attributes": True}

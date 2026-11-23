"""Auth router — US-01 User Account Onboarding.

Endpoints
---------
POST /api/v1/auth/signup    Create a user, a personal team, and an admin membership.
POST /api/v1/auth/login     Exchange credentials for an access + refresh token pair.
POST /api/v1/auth/refresh   Exchange a refresh token for a new access + refresh pair.
GET  /api/v1/auth/me        Return the profile of the authenticated user.

All routes are thin: validation lives in schemas, business logic stays here.
"""

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.password import hash_password, verify_password
from app.auth.schemas import (
    LoginRequest,
    RefreshRequest,
    SignupRequest,
    TeamInResponse,
    TokenResponse,
    UserResponse,
)
from app.auth.tokens import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)
from app.db.models import Team, TeamMembership, TeamRole, User
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_token_pair(user: User) -> TokenResponse:
    """Build an access + refresh token pair for *user*."""
    payload = {"sub": str(user.id)}
    return TokenResponse(
        access_token=create_access_token(payload),
        refresh_token=create_refresh_token(payload),
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    body: SignupRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Create a new user account, a personal team, and an admin membership.

    Returns a JWT pair so the user is immediately logged in after signup.
    Rejects duplicate e-mail addresses with HTTP 409.
    """
    # Check for duplicate email before touching the DB (fast fail).
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists.",
        )

    user = User(
        email=body.email,
        full_name=body.full_name,
        password_hash=hash_password(body.password),
    )
    team = Team(name=body.team_name or f"My Team {uuid.uuid4()}")
    try:
        db.add(user)
        await db.flush()
    except IntegrityError as err:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists.",
        ) from err

    try:
        db.add(team)
        await db.flush()
    except IntegrityError as err:
        await db.rollback()
        raise HTTPException(status_code=409, detail="This team name is already in use.") from err

    db.add(TeamMembership(team_id=team.id, user_id=user.id, role=TeamRole.admin))
    await db.flush()

    logger.info("New user registered: user_id=%s team_id=%s", user.id, team.id)
    return _make_token_pair(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Exchange valid credentials for a JWT access + refresh pair.

    Returns HTTP 401 for both wrong email and wrong password — deliberately
    the same error to avoid leaking which part was incorrect (AC-01.4).
    """
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    # Deliberately return the same error for wrong email and wrong password
    # to avoid leaking which part was incorrect (AC-01.4).
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled.",
        )

    return _make_token_pair(user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Exchange a valid refresh token for a new access + refresh token pair.

    Validates that the token is a refresh token (not an access token) and that
    the referenced user still exists and is active.
    """
    payload = decode_refresh_token(body.refresh_token)
    user_id_raw = payload.get("sub")
    if not user_id_raw:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")

    result = await db.execute(select(User).where(User.id == uuid.UUID(str(user_id_raw))))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")

    return _make_token_pair(user)


@router.get("/me", response_model=UserResponse)
async def me(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """Return the profile of the currently authenticated user including their active team.

    Active team = most recently joined team (Sprint 4 day-1 decision 1).
    """
    stmt = (
        select(TeamMembership, Team)
        .join(Team, TeamMembership.team_id == Team.id)
        .where(
            TeamMembership.user_id == current_user.id,
            Team.deleted_at.is_(None),
        )
        .order_by(TeamMembership.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    row = result.first()

    team_info: TeamInResponse | None = None
    if row is not None:
        membership, team = row
        team_info = TeamInResponse(id=team.id, name=team.name, role=membership.role)

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        team=team_info,
    )

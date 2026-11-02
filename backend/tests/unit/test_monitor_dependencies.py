"""Unit tests for monitor dependencies and RBAC authorization (US-02, US-19)."""

from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models import Team, TeamMembership, TeamRole, User
from app.modules.monitors.dependencies import (
    TeamContext,
    get_team_context,
    require_monitor_read,
    require_monitor_write,
)

_SQLITE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture()
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(_SQLITE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_get_team_context_resolves_primary_membership(db_session: AsyncSession) -> None:
    user = User(
        id=uuid4(),
        email="test@example.com",
        full_name="Test User",
        password_hash="fakehash",
    )
    team = Team(id=uuid4(), name="Primary Team")
    membership = TeamMembership(
        id=uuid4(),
        team_id=team.id,
        user_id=user.id,
        role=TeamRole.admin,
    )
    db_session.add_all([user, team, membership])
    await db_session.flush()

    context = await get_team_context(
        current_user=user,
        db=db_session,
    )
    assert context.user.id == user.id
    assert context.team.id == team.id
    assert context.role == TeamRole.admin


@pytest.mark.asyncio
async def test_get_team_context_resolves_requested_team_id(db_session: AsyncSession) -> None:
    user = User(
        id=uuid4(),
        email="multi@example.com",
        full_name="Multi Team User",
        password_hash="fakehash",
    )
    team1 = Team(id=uuid4(), name="Team 1")
    team2 = Team(id=uuid4(), name="Team 2")
    m1 = TeamMembership(id=uuid4(), team_id=team1.id, user_id=user.id, role=TeamRole.read_only)
    m2 = TeamMembership(id=uuid4(), team_id=team2.id, user_id=user.id, role=TeamRole.operator)
    db_session.add_all([user, team1, team2, m1, m2])
    await db_session.flush()

    # Query with team2 ID
    context = await get_team_context(
        current_user=user,
        db=db_session,
        team_id=team2.id,
    )
    assert context.team.id == team2.id
    assert context.role == TeamRole.operator


@pytest.mark.asyncio
async def test_get_team_context_rejects_unauthorized_team(db_session: AsyncSession) -> None:
    user = User(
        id=uuid4(),
        email="other@example.com",
        full_name="Other User",
        password_hash="fakehash",
    )
    other_team = Team(id=uuid4(), name="Other Team")
    db_session.add_all([user, other_team])
    await db_session.flush()

    with pytest.raises(HTTPException) as exc_info:
        await get_team_context(
            current_user=user,
            db=db_session,
            team_id=other_team.id,
        )
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_get_team_context_rejects_user_with_no_teams(db_session: AsyncSession) -> None:
    orphan_user = User(
        id=uuid4(),
        email="orphan@example.com",
        full_name="Orphan",
        password_hash="fakehash",
    )
    db_session.add(orphan_user)
    await db_session.flush()

    with pytest.raises(HTTPException) as exc_info:
        await get_team_context(current_user=orphan_user, db=db_session)
    assert exc_info.value.status_code == 403


def test_require_monitor_roles() -> None:
    user = User(id=uuid4(), email="a@a.com", full_name="A", password_hash="h")
    team = Team(id=uuid4(), name="T")

    admin_ctx = TeamContext(user=user, team=team, role=TeamRole.admin)
    op_ctx = TeamContext(user=user, team=team, role=TeamRole.operator)
    ro_ctx = TeamContext(user=user, team=team, role=TeamRole.read_only)

    # Read role allowed for all
    assert require_monitor_read(admin_ctx) == admin_ctx
    assert require_monitor_read(op_ctx) == op_ctx
    assert require_monitor_read(ro_ctx) == ro_ctx

    # Write role allowed for admin and operator, rejected for read_only
    assert require_monitor_write(admin_ctx) == admin_ctx
    assert require_monitor_write(op_ctx) == op_ctx
    with pytest.raises(HTTPException) as exc_info:
        require_monitor_write(ro_ctx)
    assert exc_info.value.status_code == 403
    assert "read_only" in str(exc_info.value.detail)

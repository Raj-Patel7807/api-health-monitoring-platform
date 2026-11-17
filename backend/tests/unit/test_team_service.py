"""Unit tests for Team Member management service (US-19).

Covers:
- Listing members of a team
- Adding an existing user to a team
- 404 on unknown email
- 409 on duplicate team membership
- Role updates
- 409 on last admin demotion
- Successfully demoting an admin when other admins exist
- 404 when managing a user from another team
"""

from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models import Team, TeamMembership, TeamRole, User
from app.modules.team.service import (
    add_team_member,
    list_team_members,
    update_team_member_role,
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
async def test_list_team_members(db_session: AsyncSession) -> None:
    """Members are listed with their role and user details."""
    team = Team(id=uuid4(), name="Alpha Team")
    u1 = User(
        id=uuid4(),
        email="u1@test.com",
        full_name="User One",
        password_hash="hash",
    )
    u2 = User(
        id=uuid4(),
        email="u2@test.com",
        full_name="User Two",
        password_hash="hash",
    )

    db_session.add_all([team, u1, u2])

    m1 = TeamMembership(team_id=team.id, user_id=u1.id, role=TeamRole.admin)
    m2 = TeamMembership(team_id=team.id, user_id=u2.id, role=TeamRole.operator)
    db_session.add_all([m1, m2])
    await db_session.commit()

    members = await list_team_members(db_session, team.id)
    assert len(members) == 2
    assert members[0].user_id == u1.id
    assert members[0].email == "u1@test.com"
    assert members[0].role == TeamRole.admin

    assert members[1].user_id == u2.id
    assert members[1].email == "u2@test.com"
    assert members[1].role == TeamRole.operator


@pytest.mark.asyncio
async def test_add_team_member_success(db_session: AsyncSession) -> None:
    """Admin can attach an existing user by email."""
    team = Team(id=uuid4(), name="Beta Team")
    user = User(
        id=uuid4(),
        email="new_member@test.com",
        full_name="New Member",
        password_hash="hash",
    )
    db_session.add_all([team, user])
    await db_session.commit()

    res = await add_team_member(db_session, team.id, "new_member@test.com", TeamRole.read_only)
    assert res.user_id == user.id
    assert res.email == "new_member@test.com"
    assert res.role == TeamRole.read_only


@pytest.mark.asyncio
async def test_add_team_member_unknown_email_404(db_session: AsyncSession) -> None:
    """Adding an email that does not exist in users returns 404."""
    team = Team(id=uuid4(), name="Gamma Team")
    db_session.add(team)
    await db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await add_team_member(db_session, team.id, "nonexistent@test.com", TeamRole.operator)

    assert exc_info.value.status_code == 404
    assert "User not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_add_team_member_duplicate_409(db_session: AsyncSession) -> None:
    """Adding an existing member returns 409 conflict."""
    team = Team(id=uuid4(), name="Delta Team")
    user = User(
        id=uuid4(),
        email="existing@test.com",
        full_name="Existing User",
        password_hash="hash",
    )
    db_session.add_all([team, user])
    membership = TeamMembership(team_id=team.id, user_id=user.id, role=TeamRole.operator)
    db_session.add(membership)
    await db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await add_team_member(db_session, team.id, "existing@test.com", TeamRole.read_only)

    assert exc_info.value.status_code == 409
    assert "already a member" in exc_info.value.detail


@pytest.mark.asyncio
async def test_update_team_member_role_success(db_session: AsyncSession) -> None:
    """Promoting an operator to admin succeeds."""
    team = Team(id=uuid4(), name="Epsilon Team")
    admin = User(
        id=uuid4(),
        email="admin@test.com",
        full_name="Admin",
        password_hash="hash",
    )
    op = User(
        id=uuid4(),
        email="op@test.com",
        full_name="Operator",
        password_hash="hash",
    )
    db_session.add_all([team, admin, op])

    m_admin = TeamMembership(team_id=team.id, user_id=admin.id, role=TeamRole.admin)
    m_op = TeamMembership(team_id=team.id, user_id=op.id, role=TeamRole.operator)
    db_session.add_all([m_admin, m_op])
    await db_session.commit()

    res = await update_team_member_role(db_session, team.id, op.id, TeamRole.admin)
    assert res.user_id == op.id
    assert res.role == TeamRole.admin


@pytest.mark.asyncio
async def test_update_team_member_role_demote_last_admin_409(
    db_session: AsyncSession,
) -> None:
    """Demoting the only admin on a team raises 409."""
    team = Team(id=uuid4(), name="Zeta Team")
    admin = User(
        id=uuid4(),
        email="sole_admin@test.com",
        full_name="Sole Admin",
        password_hash="hash",
    )
    db_session.add_all([team, admin])
    m_admin = TeamMembership(team_id=team.id, user_id=admin.id, role=TeamRole.admin)
    db_session.add(m_admin)
    await db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await update_team_member_role(db_session, team.id, admin.id, TeamRole.operator)

    assert exc_info.value.status_code == 409
    assert "last remaining admin" in exc_info.value.detail


@pytest.mark.asyncio
async def test_update_team_member_role_demote_admin_when_multiple(
    db_session: AsyncSession,
) -> None:
    """Demoting an admin when another admin exists succeeds."""
    team = Team(id=uuid4(), name="Eta Team")
    a1 = User(id=uuid4(), email="a1@test.com", full_name="A1", password_hash="hash")
    a2 = User(id=uuid4(), email="a2@test.com", full_name="A2", password_hash="hash")
    db_session.add_all([team, a1, a2])

    m1 = TeamMembership(team_id=team.id, user_id=a1.id, role=TeamRole.admin)
    m2 = TeamMembership(team_id=team.id, user_id=a2.id, role=TeamRole.admin)
    db_session.add_all([m1, m2])
    await db_session.commit()

    res = await update_team_member_role(db_session, team.id, a1.id, TeamRole.operator)
    assert res.user_id == a1.id
    assert res.role == TeamRole.operator


@pytest.mark.asyncio
async def test_update_team_member_role_cross_team_404(
    db_session: AsyncSession,
) -> None:
    """Managing a user belonging to another team returns 404."""
    team_a = Team(id=uuid4(), name="Team A")
    team_b = Team(id=uuid4(), name="Team B")
    user_b = User(id=uuid4(), email="b@test.com", full_name="User B", password_hash="hash")
    db_session.add_all([team_a, team_b, user_b])
    m_b = TeamMembership(team_id=team_b.id, user_id=user_b.id, role=TeamRole.operator)
    db_session.add(m_b)
    await db_session.commit()

    # Team A tries to modify user_b
    with pytest.raises(HTTPException) as exc_info:
        await update_team_member_role(db_session, team_a.id, user_b.id, TeamRole.read_only)

    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail.lower()

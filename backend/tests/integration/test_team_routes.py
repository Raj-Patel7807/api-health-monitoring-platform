"""Integration tests for Team Member management endpoints (US-19, Issue #66).

Uses an async SQLite in-memory database to test the team endpoints:
- GET /api/v1/team/members (admin, operator allowed; read_only 403; team-scoped)
- POST /api/v1/team/members (admin only; 404 on unknown email; 409 duplicate; role validation)
- PATCH /api/v1/team/members/{user_id} (admin only; 409 last admin; 404 cross-team)
"""

from collections.abc import AsyncGenerator, Generator
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_db
from app.main import app

# ---------------------------------------------------------------------------
# Test database — async SQLite in-memory
# ---------------------------------------------------------------------------

_SQLITE_URL = "sqlite+aiosqlite:///:memory:"
_engine = create_async_engine(_SQLITE_URL, echo=False)
_TestSessionFactory = async_sessionmaker(_engine, expire_on_commit=False)


async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with _TestSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest_asyncio.fixture(autouse=True, scope="session")
async def _create_tables() -> AsyncGenerator[None, None]:
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture()
async def client() -> AsyncGenerator[AsyncClient, None]:
    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Settings patch for predictable JWT
# ---------------------------------------------------------------------------

_TEST_SECRET = "integration-test-secret-long-enough-for-hs256"


@pytest.fixture(autouse=True)
def _patch_settings(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    from app.core import config as cfg

    cfg.get_settings.cache_clear()
    monkeypatch.setenv("JWT_SECRET_KEY", _TEST_SECRET)
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
    monkeypatch.setenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")
    yield
    cfg.get_settings.cache_clear()


async def _register_user(
    client: AsyncClient,
    email: str,
    team_name: str,
    full_name: str = "Test User",
) -> dict:
    resp = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "full_name": full_name,
            "password": "password123",
            "team_name": team_name,
        },
    )
    assert resp.status_code == 201
    auth_data = resp.json()
    token = auth_data["access_token"]
    me_resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    user_data = me_resp.json()
    return {
        "access_token": token,
        "refresh_token": auth_data["refresh_token"],
        "user": user_data,
    }


# ---------------------------------------------------------------------------
# Tests: GET /api/v1/team/members
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_team_members_unauthenticated(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/team/members")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_team_members_admin_and_operator(client: AsyncClient) -> None:
    # 1. Admin registers
    admin_auth = await _register_user(
        client, "admin_list@test.com", "List Team", full_name="Admin List"
    )
    admin_headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

    # Admin lists members
    list_resp = await client.get("/api/v1/team/members", headers=admin_headers)
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["email"] == "admin_list@test.com"
    assert data["items"][0]["role"] == "admin"
    assert data["items"][0]["full_name"] == "Admin List"

    # 2. Add an operator
    op_auth = await _register_user(
        client, "op_list@test.com", "Op Independent", full_name="Op List"
    )
    add_resp = await client.post(
        "/api/v1/team/members",
        json={"email": "op_list@test.com", "role": "operator"},
        headers=admin_headers,
    )
    assert add_resp.status_code == 201

    # Operator gets members
    async with _TestSessionFactory() as session:
        membership = (
            await session.execute(
                Base.metadata.tables["team_memberships"]
                .select()
                .where(
                    Base.metadata.tables["team_memberships"].c.user_id
                    == UUID(op_auth["user"]["id"])
                )
                .where(Base.metadata.tables["team_memberships"].c.role == "operator")
            )
        ).first()
        target_team_id = membership.team_id

    op_headers = {
        "Authorization": f"Bearer {op_auth['access_token']}",
        "X-Team-ID": str(target_team_id),
    }

    op_list_resp = await client.get("/api/v1/team/members", headers=op_headers)
    assert op_list_resp.status_code == 200
    assert len(op_list_resp.json()["items"]) == 2


@pytest.mark.asyncio
async def test_get_team_members_read_only_forbidden(client: AsyncClient) -> None:
    admin_auth = await _register_user(client, "admin_ro_test@test.com", "RO Test Team")
    admin_headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

    ro_auth = await _register_user(client, "ro_member@test.com", "RO Team Indep")
    add_resp = await client.post(
        "/api/v1/team/members",
        json={"email": "ro_member@test.com", "role": "read_only"},
        headers=admin_headers,
    )
    assert add_resp.status_code == 201

    # Get target team_id
    async with _TestSessionFactory() as session:
        membership = (
            await session.execute(
                Base.metadata.tables["team_memberships"]
                .select()
                .where(
                    Base.metadata.tables["team_memberships"].c.user_id
                    == UUID(ro_auth["user"]["id"])
                )
                .where(Base.metadata.tables["team_memberships"].c.role == "read_only")
            )
        ).first()
        team_id = membership.team_id

    ro_headers = {
        "Authorization": f"Bearer {ro_auth['access_token']}",
        "X-Team-ID": str(team_id),
    }

    # read_only user is forbidden from listing members
    ro_list_resp = await client.get("/api/v1/team/members", headers=ro_headers)
    assert ro_list_resp.status_code == 403


# ---------------------------------------------------------------------------
# Tests: POST /api/v1/team/members
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_team_member_success(client: AsyncClient) -> None:
    admin_auth = await _register_user(client, "admin_add@test.com", "Add Team")
    admin_headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

    candidate = await _register_user(client, "candidate@test.com", "Candidate Team", "New Member")

    resp = await client.post(
        "/api/v1/team/members",
        json={"email": "candidate@test.com", "role": "operator"},
        headers=admin_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "candidate@test.com"
    assert data["role"] == "operator"
    assert data["full_name"] == "New Member"
    assert data["user_id"] == candidate["user"]["id"]


@pytest.mark.asyncio
async def test_post_team_member_unknown_email_404(client: AsyncClient) -> None:
    admin_auth = await _register_user(client, "admin_404@test.com", "404 Team")
    admin_headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

    resp = await client.post(
        "/api/v1/team/members",
        json={"email": "nonexistent@test.com", "role": "operator"},
        headers=admin_headers,
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_post_team_member_duplicate_409(client: AsyncClient) -> None:
    admin_auth = await _register_user(client, "admin_dup@test.com", "Dup Team")
    admin_headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

    await _register_user(client, "dup_candidate@test.com", "Dup Indep")

    # Add first time
    resp1 = await client.post(
        "/api/v1/team/members",
        json={"email": "dup_candidate@test.com", "role": "read_only"},
        headers=admin_headers,
    )
    assert resp1.status_code == 201

    # Add second time -> 409
    resp2 = await client.post(
        "/api/v1/team/members",
        json={"email": "dup_candidate@test.com", "role": "operator"},
        headers=admin_headers,
    )
    assert resp2.status_code == 409
    assert "already a member" in resp2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_post_team_member_invalid_role_422(client: AsyncClient) -> None:
    admin_auth = await _register_user(client, "admin_badrole@test.com", "BadRole Team")
    admin_headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

    resp = await client.post(
        "/api/v1/team/members",
        json={"email": "admin_badrole@test.com", "role": "superadmin"},
        headers=admin_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_post_team_member_forbidden_for_non_admin(client: AsyncClient) -> None:
    admin_auth = await _register_user(client, "admin_perm@test.com", "Perm Team")
    admin_headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

    op_auth = await _register_user(client, "op_perm@test.com", "Op Perm Team")
    await _register_user(client, "third_perm@test.com", "Third Team")

    # Add op to Perm Team
    await client.post(
        "/api/v1/team/members",
        json={"email": "op_perm@test.com", "role": "operator"},
        headers=admin_headers,
    )

    async with _TestSessionFactory() as session:
        membership = (
            await session.execute(
                Base.metadata.tables["team_memberships"]
                .select()
                .where(
                    Base.metadata.tables["team_memberships"].c.user_id
                    == UUID(op_auth["user"]["id"])
                )
                .where(Base.metadata.tables["team_memberships"].c.role == "operator")
            )
        ).first()
        team_id = membership.team_id

    op_headers = {
        "Authorization": f"Bearer {op_auth['access_token']}",
        "X-Team-ID": str(team_id),
    }

    # Operator cannot add members
    resp = await client.post(
        "/api/v1/team/members",
        json={"email": "third_perm@test.com", "role": "read_only"},
        headers=op_headers,
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Tests: PATCH /api/v1/team/members/{user_id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patch_team_member_role_success(client: AsyncClient) -> None:
    admin_auth = await _register_user(client, "admin_patch@test.com", "Patch Team")
    admin_headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

    member_auth = await _register_user(client, "member_patch@test.com", "Member Patch Team")
    member_user_id = member_auth["user"]["id"]

    # Add as read_only
    await client.post(
        "/api/v1/team/members",
        json={"email": "member_patch@test.com", "role": "read_only"},
        headers=admin_headers,
    )

    # Promote to operator
    resp = await client.patch(
        f"/api/v1/team/members/{member_user_id}",
        json={"role": "operator"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "operator"


@pytest.mark.asyncio
async def test_patch_team_member_last_admin_demotion_409(client: AsyncClient) -> None:
    admin_auth = await _register_user(client, "admin_solo@test.com", "Solo Admin Team")
    admin_headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    admin_user_id = admin_auth["user"]["id"]

    # Attempt to demote self (the only admin) to operator -> 409
    resp = await client.patch(
        f"/api/v1/team/members/{admin_user_id}",
        json={"role": "operator"},
        headers=admin_headers,
    )
    assert resp.status_code == 409
    assert "last remaining admin" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_patch_team_member_demote_admin_when_multiple_admins(client: AsyncClient) -> None:
    admin1_auth = await _register_user(client, "admin1_multi@test.com", "Multi Admin Team")
    admin1_headers = {"Authorization": f"Bearer {admin1_auth['access_token']}"}
    admin1_user_id = admin1_auth["user"]["id"]

    await _register_user(client, "admin2_multi@test.com", "Admin2 Indep")

    # Add second user as admin
    add_resp = await client.post(
        "/api/v1/team/members",
        json={"email": "admin2_multi@test.com", "role": "admin"},
        headers=admin1_headers,
    )
    assert add_resp.status_code == 201

    # Now demote admin1 -> succeeds because admin2 exists
    demote_resp = await client.patch(
        f"/api/v1/team/members/{admin1_user_id}",
        json={"role": "operator"},
        headers=admin1_headers,
    )
    assert demote_resp.status_code == 200
    assert demote_resp.json()["role"] == "operator"


@pytest.mark.asyncio
async def test_patch_team_member_cross_team_404(client: AsyncClient) -> None:
    team_a = await _register_user(client, "admin_a@test.com", "Team A")
    headers_a = {"Authorization": f"Bearer {team_a['access_token']}"}

    team_b = await _register_user(client, "admin_b@test.com", "Team B")
    user_b_id = team_b["user"]["id"]

    # Team A tries to modify role of Team B member -> 404 (not found in caller's team)
    resp = await client.patch(
        f"/api/v1/team/members/{user_b_id}",
        json={"role": "operator"},
        headers=headers_a,
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_patch_team_member_unknown_user_404(client: AsyncClient) -> None:
    admin_auth = await _register_user(client, "admin_nonexist@test.com", "Nonexist Team")
    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

    random_id = uuid4()
    resp = await client.patch(
        f"/api/v1/team/members/{random_id}",
        json={"role": "operator"},
        headers=headers,
    )
    assert resp.status_code == 404

"""Integration tests for auth routes (US-01).

These tests spin up the real FastAPI app but swap the database for an
async SQLite in-memory DB so they run without a live PostgreSQL.

Coverage:
    POST /api/v1/auth/signup    — happy path, duplicate email (409)
    POST /api/v1/auth/login     — correct credentials (200), wrong password (401)
    POST /api/v1/auth/refresh   — valid refresh token (200)
    GET  /api/v1/auth/me        — authenticated (200), no Authorization header (403)
"""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import Base
from app.db.session import get_db
from app.main import app

# ---------------------------------------------------------------------------
# Test database — async SQLite in-memory (no real PostgreSQL needed)
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
    """Create all ORM tables once for the entire test session."""
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture()
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client wired to the FastAPI app with a DB override."""
    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Settings override — use a known JWT secret so tests are deterministic
# ---------------------------------------------------------------------------

_TEST_SECRET = "integration-test-secret-long-enough-for-hs256"


@pytest.fixture(autouse=True)
def _patch_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config as cfg

    cfg.get_settings.cache_clear()
    monkeypatch.setenv("JWT_SECRET_KEY", _TEST_SECRET)
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
    monkeypatch.setenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")
    yield
    cfg.get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Common test payload
# ---------------------------------------------------------------------------

_SIGNUP_PAYLOAD = {
    "email": "alice@example.com",
    "full_name": "Alice Example",
    "password": "password123",
    "team_name": "Alice Team",
}


# ---------------------------------------------------------------------------
# Signup tests
# ---------------------------------------------------------------------------


async def test_signup_returns_201_and_tokens(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/auth/signup", json=_SIGNUP_PAYLOAD)
    assert resp.status_code == 201
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


async def test_signup_duplicate_email_returns_409(client: AsyncClient) -> None:
    payload = {**_SIGNUP_PAYLOAD, "email": "bob@example.com"}
    r1 = await client.post("/api/v1/auth/signup", json=payload)
    assert r1.status_code == 201

    r2 = await client.post("/api/v1/auth/signup", json=payload)
    assert r2.status_code == 409


async def test_signup_short_password_returns_422(client: AsyncClient) -> None:
    payload = {**_SIGNUP_PAYLOAD, "email": "carol@example.com", "password": "short"}
    resp = await client.post("/api/v1/auth/signup", json=payload)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Login tests
# ---------------------------------------------------------------------------


async def test_login_correct_credentials_returns_200(client: AsyncClient) -> None:
    signup_payload = {**_SIGNUP_PAYLOAD, "email": "dave@example.com"}
    await client.post("/api/v1/auth/signup", json=signup_payload)

    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "dave@example.com", "password": "password123"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body


async def test_login_wrong_password_returns_401(client: AsyncClient) -> None:
    signup_payload = {**_SIGNUP_PAYLOAD, "email": "eve@example.com"}
    await client.post("/api/v1/auth/signup", json=signup_payload)

    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "eve@example.com", "password": "wrong-password"},
    )
    assert resp.status_code == 401


async def test_login_unknown_email_returns_401(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "whatever"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Refresh tests
# ---------------------------------------------------------------------------


async def test_refresh_returns_new_token_pair(client: AsyncClient) -> None:
    signup_payload = {**_SIGNUP_PAYLOAD, "email": "frank@example.com"}
    signup_resp = await client.post("/api/v1/auth/signup", json=signup_payload)
    refresh_token = signup_resp.json()["refresh_token"]

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body


async def test_refresh_with_access_token_returns_401(client: AsyncClient) -> None:
    """Sending an access token to /refresh must be rejected (type confusion guard)."""
    signup_payload = {**_SIGNUP_PAYLOAD, "email": "grace@example.com"}
    signup_resp = await client.post("/api/v1/auth/signup", json=signup_payload)
    access_token = signup_resp.json()["access_token"]

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# /me tests
# ---------------------------------------------------------------------------


async def test_me_authenticated_returns_user_profile(client: AsyncClient) -> None:
    signup_payload = {**_SIGNUP_PAYLOAD, "email": "heidi@example.com"}
    signup_resp = await client.post("/api/v1/auth/signup", json=signup_payload)
    access_token = signup_resp.json()["access_token"]

    resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "heidi@example.com"
    assert body["full_name"] == "Alice Example"
    assert "id" in body


async def test_me_no_token_returns_401(client: AsyncClient) -> None:
    """No Authorization header → 401. FastAPI's HTTPBearer returns 403 on older
    versions and 401 on newer ones; we assert the actual unauthenticated status."""
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code in (401, 403)

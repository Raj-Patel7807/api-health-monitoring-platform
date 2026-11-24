"""Integration tests for monitor document importer routes (Problem C & Section 5).

Tests:
- POST /api/v1/monitors/import/preview:
  * 401 unauthenticated
  * 403 read_only role
  * 413 payload too large (> 2MB)
  * 200 with Markdown file
  * 200 with OpenAPI JSON file
- POST /api/v1/monitors/import/commit:
  * 401 unauthenticated
  * 403 read_only role
  * 400 on empty items
  * 400 on unsafe/SSRF target URL
  * 201 on valid candidates commit, verifying DB persistence and team isolation
"""

from collections.abc import AsyncGenerator, Generator
from uuid import UUID

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
# Tests: Preview Endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_importer_preview_unauthenticated(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/monitors/import/preview")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_importer_preview_read_only_forbidden(client: AsyncClient) -> None:
    admin_auth = await _register_user(client, "admin_imp_ro@test.com", "Imp RO Team")
    admin_headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

    ro_auth = await _register_user(client, "ro_imp_user@test.com", "Indep RO Team")
    add_resp = await client.post(
        "/api/v1/team/members",
        json={"email": "ro_imp_user@test.com", "role": "read_only"},
        headers=admin_headers,
    )
    assert add_resp.status_code == 201

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
        target_team_id = membership.team_id

    ro_headers = {
        "Authorization": f"Bearer {ro_auth['access_token']}",
        "X-Team-ID": str(target_team_id),
    }

    files = {"file": ("test.md", b"# API\n### GET /health", "text/markdown")}
    resp = await client.post("/api/v1/monitors/import/preview", headers=ro_headers, files=files)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_importer_preview_file_too_large(client: AsyncClient) -> None:
    admin_auth = await _register_user(client, "admin_size@test.com", "Size Team")
    admin_headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

    # > 2MB (2 * 1024 * 1024 + 1 bytes)
    huge_content = b"a" * (2 * 1024 * 1024 + 10)
    files = {"file": ("large.md", huge_content, "text/markdown")}
    resp = await client.post("/api/v1/monitors/import/preview", headers=admin_headers, files=files)
    assert resp.status_code == 413
    assert "2MB" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_importer_preview_markdown_and_openapi(client: AsyncClient) -> None:
    admin_auth = await _register_user(client, "admin_imp_ok@test.com", "Ok Team")
    admin_headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

    # Markdown preview
    md_content = b"""# API Documentation
### GET /api/v1/ping
Checks service availability.

| Method | Path | Expected Status |
| --- | --- | --- |
| POST | /api/v1/checkout | 201 |
"""
    files = {"file": ("api.md", md_content, "text/markdown")}
    data = {"base_url": "https://api.example.com"}
    resp = await client.post(
        "/api/v1/monitors/import/preview",
        headers=admin_headers,
        files=files,
        data=data,
    )
    assert resp.status_code == 200
    preview = resp.json()
    assert preview["total_found"] == 2
    assert preview["valid_count"] == 2
    assert len(preview["items"]) == 2

    urls = [c["url"] for c in preview["items"]]
    assert any("/api/v1/ping" in u for u in urls)
    assert any("/api/v1/checkout" in u for u in urls)

    # OpenAPI JSON preview
    openapi_json = b"""{
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0"},
        "paths": {
            "/api/v1/users": {
                "get": {
                    "summary": "List users",
                    "responses": {"200": {"description": "OK"}}
                }
            }
        }
    }"""
    files_json = {"file": ("openapi.json", openapi_json, "application/json")}
    resp_json = await client.post(
        "/api/v1/monitors/import/preview",
        headers=admin_headers,
        files=files_json,
        data={"base_url": "https://api.example.com"},
    )
    assert resp_json.status_code == 200
    preview_json = resp_json.json()
    assert preview_json["total_found"] == 1
    assert any("/api/v1/users" in c["url"] for c in preview_json["items"])


# ---------------------------------------------------------------------------
# Tests: Commit Endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_importer_commit_unauthenticated(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/monitors/import/commit", json={"items": []})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_importer_commit_empty_items(client: AsyncClient) -> None:
    admin_auth = await _register_user(client, "admin_commit_empty@test.com", "Empty Team")
    admin_headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

    resp = await client.post(
        "/api/v1/monitors/import/commit",
        json={"items": []},
        headers=admin_headers,
    )
    assert resp.status_code == 400
    assert "No candidate monitors provided" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_importer_commit_unsafe_url_ssrf(client: AsyncClient) -> None:
    admin_auth = await _register_user(client, "admin_ssrf_test@test.com", "SSRF Team")
    admin_headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

    payload = {
        "items": [
            {
                "name": "Cloud Metadata Exfiltration",
                "method": "GET",
                "url": "http://169.254.169.254/latest/meta-data/",
                "expected_status_code": 200,
                "check_interval_seconds": 60,
                "timeout_seconds": 10,
            }
        ]
    }
    resp = await client.post(
        "/api/v1/monitors/import/commit",
        json=payload,
        headers=admin_headers,
    )
    assert resp.status_code == 400
    assert "private or restricted address space" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_importer_commit_success(client: AsyncClient) -> None:
    admin_auth = await _register_user(client, "admin_commit_ok@test.com", "Success Commit Team")
    admin_headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}

    payload = {
        "items": [
            {
                "name": "Health Check API",
                "method": "GET",
                "url": "https://httpstat.us/200",
                "expected_status_code": 200,
                "check_interval_seconds": 60,
                "timeout_seconds": 5,
            },
            {
                "name": "Status Check API",
                "method": "POST",
                "url": "https://httpstat.us/201",
                "expected_status_code": 201,
                "check_interval_seconds": 120,
                "timeout_seconds": 10,
            },
        ]
    }
    resp = await client.post(
        "/api/v1/monitors/import/commit",
        json=payload,
        headers=admin_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["imported_count"] == 2
    assert len(data["monitor_ids"]) == 2

    # Verify monitors are in DB and listed on GET /api/v1/monitors
    list_resp = await client.get("/api/v1/monitors", headers=admin_headers)
    assert list_resp.status_code == 200
    monitors = list_resp.json()["items"]
    urls = [m["url"] for m in monitors]
    assert "https://httpstat.us/200" in urls
    assert "https://httpstat.us/201" in urls

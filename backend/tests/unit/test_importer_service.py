"""Unit tests for API documentation parser and SSRF security."""

import json
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.modules.importer.parser import parse_api_documentation
from app.modules.importer.schemas import CandidateMonitor, ImportCommitRequest
from app.modules.importer.service import commit_import_service, preview_import_service
from app.modules.importer.ssrf import is_safe_url
from app.modules.monitors.models import HttpMethod, Monitor

_SQLITE_URL = "sqlite+aiosqlite:///:memory:"


def test_ssrf_blocks_private_and_loopback_ips() -> None:
    # Loopback
    safe, err = is_safe_url("http://127.0.0.1/status")
    assert safe is False
    assert "restricted" in (err or "").lower() or "private" in (err or "").lower()

    safe, err = is_safe_url("http://localhost:8000/api")
    assert safe is False

    # Private RFC 1918
    safe, _ = is_safe_url("http://10.0.0.5/health")
    assert safe is False

    safe, _ = is_safe_url("http://172.16.5.1:3000/metrics")
    assert safe is False

    safe, _ = is_safe_url("http://192.168.1.1/ping")
    assert safe is False

    # Cloud metadata
    safe, _ = is_safe_url("http://169.254.169.254/latest/meta-data")
    assert safe is False

    # Unsupported schemes
    safe, err = is_safe_url("ftp://example.com/file")
    assert safe is False
    assert "scheme" in (err or "").lower()

    safe, _ = is_safe_url("file:///etc/passwd")
    assert safe is False


def test_ssrf_allows_safe_public_urls_and_relative_paths() -> None:
    safe, _ = is_safe_url("https://example.com/api/v1/health")
    assert safe is True

    safe, _ = is_safe_url("http://api.github.com/users")
    assert safe is True

    # Relative paths allowed only when flag is set
    safe_rel, _ = is_safe_url("/api/v1/monitors", allow_relative=True)
    assert safe_rel is True

    unsafe_rel, _ = is_safe_url("/api/v1/monitors", allow_relative=False)
    assert unsafe_rel is False


def test_parse_markdown_headers_and_tables() -> None:
    doc = """
# API Documentation

### GET /api/v1/health
Expected status: 200

### POST /api/v1/orders
Returns 201 Created on success.
Payload contains order items.

| Method | Endpoint | Status |
|---|---|---|
| GET | /api/v1/users | 200 |
| DELETE | /api/v1/sessions | 204 |
"""
    items = parse_api_documentation(doc, "api.md", default_base_url="https://api.mycompany.com")
    assert len(items) == 4

    # GET /api/v1/health
    m0 = next(i for i in items if i.method == HttpMethod.GET and "/api/v1/health" in i.url)
    assert m0.expected_status_code == 200
    assert m0.url == "https://api.mycompany.com/api/v1/health"
    assert m0.is_valid is True

    # POST /api/v1/orders
    m1 = next(i for i in items if i.method == HttpMethod.POST and "/api/v1/orders" in i.url)
    assert m1.expected_status_code == 201
    assert m1.is_valid is True

    # Table GET /api/v1/users
    m2 = next(i for i in items if i.method == HttpMethod.GET and "/api/v1/users" in i.url)
    assert m2.expected_status_code == 200

    # Table DELETE /api/v1/sessions
    m3 = next(i for i in items if i.method == HttpMethod.DELETE and "/api/v1/sessions" in i.url)
    assert m3.expected_status_code == 204


def test_parse_openapi_json() -> None:
    spec = {
        "openapi": "3.0.0",
        "servers": [{"url": "https://service.example.com"}],
        "paths": {
            "/api/items": {
                "get": {
                    "summary": "List Items",
                    "responses": {"200": {"description": "OK"}},
                },
                "post": {
                    "summary": "Create Item",
                    "responses": {"201": {"description": "Created"}},
                },
            }
        },
    }
    items = parse_api_documentation(json.dumps(spec), "openapi.json")
    assert len(items) == 2
    get_item = next(i for i in items if i.method == HttpMethod.GET)
    assert get_item.name == "List Items"
    assert get_item.url == "https://service.example.com/api/items"
    assert get_item.expected_status_code == 200


def test_preview_import_service() -> None:
    doc = "### GET https://api.example.com/healthz\nReturns 200"
    resp = preview_import_service(doc, "api.md")
    assert resp.filename == "api.md"
    assert resp.total_found == 1
    assert resp.valid_count == 1
    assert resp.items[0].name == "GET https://api.example.com/healthz"
    assert resp.items[0].url == "https://api.example.com/healthz"


@pytest.mark.asyncio
async def test_commit_import_service() -> None:
    engine = create_async_engine(_SQLITE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    team_id = uuid4()

    async with session_factory() as session:
        req = ImportCommitRequest(
            base_url="https://api.testservice.com",
            items=[
                CandidateMonitor(
                    name="Health Check",
                    url="/healthz",
                    method=HttpMethod.GET,
                    expected_status_code=200,
                    check_interval_seconds=30,
                    timeout_seconds=10,
                ),
                CandidateMonitor(
                    name="Ping External",
                    url="https://example.com/ping",
                    method=HttpMethod.GET,
                    expected_status_code=200,
                    check_interval_seconds=60,
                    timeout_seconds=5,
                ),
            ],
        )

        res = await commit_import_service(session, team_id, req)
        assert res.imported_count == 2
        assert len(res.monitor_ids) == 2

        # Verify persisted monitors
        m0 = await session.get(Monitor, res.monitor_ids[0])
        assert m0 is not None
        assert m0.url == "https://api.testservice.com/healthz"
        assert m0.team_id == team_id

        m1 = await session.get(Monitor, res.monitor_ids[1])
        assert m1 is not None
        assert m1.url == "https://example.com/ping"

    await engine.dispose()

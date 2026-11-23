"""Unit tests for AI incident diagnosis provider and service."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.modules.ai.provider import (
    DeterministicRuleAIProvider,
    GeminiAIProvider,
    IncidentAnalysisContext,
)
from app.modules.ai.service import get_or_generate_ai_analysis
from app.modules.incidents.models import Incident
from app.modules.monitors.models import Monitor
from app.modules.results.models import HealthCheckResult

_SQLITE_URL = "sqlite+aiosqlite:///:memory:"


def test_deterministic_provider_rules() -> None:
    provider = DeterministicRuleAIProvider()

    # 1. Timeout
    ctx_timeout = IncidentAnalysisContext(
        incident_id=str(uuid4()),
        monitor_name="Billing API",
        monitor_url="https://billing.example.com",
        failure_count=3,
        http_status_code=None,
        response_time_ms=10005,
        error_message="ReadTimeout: Operation timed out",
        is_timeout=True,
        is_connection_error=False,
        is_ssl_error=False,
    )
    res_timeout = provider.analyze(ctx_timeout)
    assert "timed out" in res_timeout.summary.lower()
    root = res_timeout.root_cause.lower()
    assert "latency" in root or "saturation" in root
    assert len(res_timeout.suggested_actions) > 0
    assert len(res_timeout.investigation_steps) > 0

    # 2. SSL Error
    ctx_ssl = IncidentAnalysisContext(
        incident_id=str(uuid4()),
        monitor_name="Auth API",
        monitor_url="https://auth.example.com",
        failure_count=3,
        http_status_code=None,
        response_time_ms=None,
        error_message="SSLError: certificate verify failed: certificate has expired",
        is_timeout=False,
        is_connection_error=False,
        is_ssl_error=True,
    )
    res_ssl = provider.analyze(ctx_ssl)
    assert "ssl/tls" in res_ssl.summary.lower()
    assert "certificate" in res_ssl.root_cause.lower()

    # 3. Connection Error
    ctx_conn = IncidentAnalysisContext(
        incident_id=str(uuid4()),
        monitor_name="Cart API",
        monitor_url="https://cart.example.com",
        failure_count=3,
        http_status_code=None,
        response_time_ms=None,
        error_message="ConnectError: [Errno 111] Connection refused",
        is_timeout=False,
        is_connection_error=True,
        is_ssl_error=False,
    )
    res_conn = provider.analyze(ctx_conn)
    assert "connection refused" in res_conn.summary.lower()

    # 4. HTTP 500
    ctx_500 = IncidentAnalysisContext(
        incident_id=str(uuid4()),
        monitor_name="Search API",
        monitor_url="https://search.example.com",
        failure_count=3,
        http_status_code=500,
        response_time_ms=250,
        error_message="Internal Server Error",
        is_timeout=False,
        is_connection_error=False,
        is_ssl_error=False,
    )
    res_500 = provider.analyze(ctx_500)
    assert "500" in res_500.summary
    assert "server" in res_500.root_cause.lower()

    # 5. HTTP 401
    ctx_401 = IncidentAnalysisContext(
        incident_id=str(uuid4()),
        monitor_name="Secret API",
        monitor_url="https://secret.example.com",
        failure_count=3,
        http_status_code=401,
        response_time_ms=45,
        error_message="Unauthorized",
        is_timeout=False,
        is_connection_error=False,
        is_ssl_error=False,
    )
    res_401 = provider.analyze(ctx_401)
    assert "authentication" in res_401.summary.lower() or "401" in res_401.summary

    # 6. HTTP 404
    ctx_404 = IncidentAnalysisContext(
        incident_id=str(uuid4()),
        monitor_name="Legacy API",
        monitor_url="https://api.example.com/legacy/v0",
        failure_count=3,
        http_status_code=404,
        response_time_ms=30,
        error_message="Not Found",
        is_timeout=False,
        is_connection_error=False,
        is_ssl_error=False,
    )
    res_404 = provider.analyze(ctx_404)
    assert "404" in res_404.summary


def test_gemini_provider_fallback() -> None:
    # Provider without key falls back directly to deterministic rules
    provider = GeminiAIProvider(api_key="")
    ctx = IncidentAnalysisContext(
        incident_id=str(uuid4()),
        monitor_name="Fallback Test",
        monitor_url="https://test.example.com",
        failure_count=3,
        http_status_code=503,
        response_time_ms=120,
        error_message="Service Unavailable",
        is_timeout=False,
        is_connection_error=False,
        is_ssl_error=False,
    )
    res = provider.analyze(ctx)
    assert "503" in res.summary
    assert res.model == "deterministic-rules"


@pytest.mark.asyncio
async def test_get_or_generate_ai_analysis_service() -> None:
    engine = create_async_engine(_SQLITE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    team_id = uuid4()
    monitor_id = uuid4()
    incident_id = uuid4()

    async with session_factory() as session:
        # Create monitor
        mon = Monitor(
            id=monitor_id,
            team_id=team_id,
            name="Checkout Service",
            url="https://checkout.example.com/pay",
            enabled=True,
        )
        session.add(mon)

        # Create incident
        inc = Incident(
            id=incident_id,
            monitor_id=monitor_id,
            status="open",
            failure_count=3,
            opened_at=datetime.now(UTC),
        )
        session.add(inc)

        # Create latest failing check result
        res = HealthCheckResult(
            id=uuid4(),
            monitor_id=monitor_id,
            status="failing",
            http_status_code=502,
            error_message="Bad Gateway from upstream proxy",
            checked_at=datetime.now(UTC),
        )
        session.add(res)
        await session.commit()

        # 1. Generate new analysis
        analysis = await get_or_generate_ai_analysis(session, incident_id, force=False)
        assert analysis is not None
        assert analysis.incident_id == incident_id
        assert "502" in analysis.summary
        assert analysis.status == "completed"
        assert len(analysis.suggested_actions) > 0

        # 2. Query again without force -> returns existing record
        analysis_cached = await get_or_generate_ai_analysis(session, incident_id, force=False)
        assert analysis_cached is not None
        assert analysis_cached.id == analysis.id

        # 3. Query with force=True -> updates existing record
        analysis_forced = await get_or_generate_ai_analysis(session, incident_id, force=True)
        assert analysis_forced is not None
        assert analysis_forced.id == analysis.id

    await engine.dispose()

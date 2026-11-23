"""Service layer for AI incident assistance."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.modules.ai.models import AIAnalysis
from app.modules.ai.provider import IncidentAnalysisContext, get_ai_provider
from app.modules.incidents.models import Incident
from app.modules.monitors.models import Monitor
from app.modules.results.models import HealthCheckResult

logger = logging.getLogger(__name__)


async def get_or_generate_ai_analysis(
    db: AsyncSession,
    incident_id: UUID,
    force: bool = False,
) -> AIAnalysis | None:
    """Retrieve or synchronously generate advisory AI analysis for an incident."""
    # 1. Check existing analysis
    stmt = select(AIAnalysis).where(AIAnalysis.incident_id == incident_id)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing is not None and not force:
        return existing

    # 2. Fetch incident, monitor, and latest result
    incident = await db.get(Incident, incident_id)
    if incident is None:
        return None

    monitor = await db.get(Monitor, incident.monitor_id)
    if monitor is None:
        return None

    res_stmt = (
        select(HealthCheckResult)
        .where(HealthCheckResult.monitor_id == monitor.id)
        .order_by(desc(HealthCheckResult.checked_at))
        .limit(1)
    )
    last_res = (await db.execute(res_stmt)).scalar_one_or_none()

    context = IncidentAnalysisContext(
        incident_id=str(incident_id),
        monitor_name=monitor.name,
        monitor_url=monitor.url,
        failure_count=incident.failure_count,
        http_status_code=last_res.http_status_code if last_res else None,
        response_time_ms=last_res.response_time_ms if last_res else None,
        error_message=last_res.error_message if last_res else None,
        is_timeout=last_res.timeout if last_res else False,
        is_connection_error=last_res.connection_error if last_res else False,
        is_ssl_error=last_res.ssl_error if last_res else False,
    )

    provider = get_ai_provider()
    analysis_res = provider.analyze(context)

    if existing is not None and force:
        existing.summary = analysis_res.summary
        existing.root_cause = analysis_res.root_cause
        existing.suggested_actions = analysis_res.suggested_actions
        existing.investigation_steps = analysis_res.investigation_steps
        existing.prevention_steps = analysis_res.prevention_steps
        existing.model = analysis_res.model
        existing.status = "completed"
        await db.commit()
        await db.refresh(existing)
        return existing

    new_analysis = AIAnalysis(
        incident_id=incident_id,
        status="completed",
        summary=analysis_res.summary,
        root_cause=analysis_res.root_cause,
        suggested_actions=analysis_res.suggested_actions,
        investigation_steps=analysis_res.investigation_steps,
        prevention_steps=analysis_res.prevention_steps,
        model=analysis_res.model,
    )
    db.add(new_analysis)
    await db.commit()
    await db.refresh(new_analysis)
    return new_analysis


def sync_generate_ai_analysis(
    session: Session,
    incident_id: UUID,
) -> AIAnalysis | None:
    """Synchronous version for use within Celery workers."""
    existing = session.execute(
        select(AIAnalysis).where(AIAnalysis.incident_id == incident_id)
    ).scalar_one_or_none()

    if existing is not None:
        return existing

    incident = session.get(Incident, incident_id)
    if incident is None:
        return None

    monitor = session.get(Monitor, incident.monitor_id)
    if monitor is None:
        return None

    last_res = session.execute(
        select(HealthCheckResult)
        .where(HealthCheckResult.monitor_id == monitor.id)
        .order_by(desc(HealthCheckResult.checked_at))
        .limit(1)
    ).scalar_one_or_none()

    context = IncidentAnalysisContext(
        incident_id=str(incident_id),
        monitor_name=monitor.name,
        monitor_url=monitor.url,
        failure_count=incident.failure_count,
        http_status_code=last_res.http_status_code if last_res else None,
        response_time_ms=last_res.response_time_ms if last_res else None,
        error_message=last_res.error_message if last_res else None,
        is_timeout=last_res.timeout if last_res else False,
        is_connection_error=last_res.connection_error if last_res else False,
        is_ssl_error=last_res.ssl_error if last_res else False,
    )

    provider = get_ai_provider()
    analysis_res = provider.analyze(context)

    analysis = AIAnalysis(
        incident_id=incident_id,
        status="completed",
        summary=analysis_res.summary,
        root_cause=analysis_res.root_cause,
        suggested_actions=analysis_res.suggested_actions,
        investigation_steps=analysis_res.investigation_steps,
        prevention_steps=analysis_res.prevention_steps,
        model=analysis_res.model,
    )
    session.add(analysis)
    session.commit()
    session.refresh(analysis)
    return analysis

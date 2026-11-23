"""FastAPI router for AI incident assistance (US-16)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.ai import service
from app.modules.ai.schemas import AIAnalysisResponse
from app.modules.incidents.models import Incident
from app.modules.monitors.dependencies import (
    TeamContext,
    require_monitor_read,
    require_monitor_write,
)
from app.modules.monitors.models import Monitor

router = APIRouter(prefix="/api/v1/incidents", tags=["ai-incident-assistance"])


@router.get("/{id}/ai-analysis", response_model=AIAnalysisResponse)
async def get_incident_ai_analysis(
    id: UUID,
    context: Annotated[TeamContext, Depends(require_monitor_read)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AIAnalysisResponse:
    """Retrieve or generate advisory AI analysis for an incident."""
    incident_stmt = (
        select(Incident)
        .join(Monitor, Incident.monitor_id == Monitor.id)
        .where(
            Incident.id == id,
            Monitor.team_id == context.team.id,
            Monitor.deleted_at.is_(None),
        )
    )
    inc_result = await db.execute(incident_stmt)
    if inc_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found.",
        )

    analysis = await service.get_or_generate_ai_analysis(db, id, force=False)
    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unable to generate AI analysis for this incident.",
        )
    return analysis  # type: ignore[return-value]


@router.post("/{id}/ai-analysis", response_model=AIAnalysisResponse)
async def trigger_incident_ai_analysis(
    id: UUID,
    context: Annotated[TeamContext, Depends(require_monitor_write)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AIAnalysisResponse:
    """Trigger or re-generate advisory AI analysis for an incident on demand."""
    incident_stmt = (
        select(Incident)
        .join(Monitor, Incident.monitor_id == Monitor.id)
        .where(
            Incident.id == id,
            Monitor.team_id == context.team.id,
            Monitor.deleted_at.is_(None),
        )
    )
    inc_result = await db.execute(incident_stmt)
    if inc_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found.",
        )

    analysis = await service.get_or_generate_ai_analysis(db, id, force=True)
    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unable to generate AI analysis for this incident.",
        )
    return analysis  # type: ignore[return-value]

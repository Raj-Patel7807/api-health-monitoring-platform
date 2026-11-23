"""Pydantic schemas for AI incident analysis."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AIAnalysisResponse(BaseModel):
    """Advisory diagnosis and recommended actions for an incident."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    incident_id: UUID
    status: str
    summary: str
    root_cause: str | None = None
    suggested_actions: list[str] = []
    investigation_steps: list[str] = []
    prevention_steps: list[str] = []
    model: str
    error_message: str | None = None
    created_at: datetime

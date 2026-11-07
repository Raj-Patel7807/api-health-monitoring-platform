"""Pydantic schemas for Incident state machine and API (US-10)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.modules.incidents.models import IncidentStatus

__all__ = [
    "IncidentDetailResponse",
    "IncidentListResponse",
    "IncidentResponse",
    "IncidentStatus",
]


class IncidentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    monitor_id: UUID
    status: IncidentStatus
    opened_at: datetime
    resolved_at: datetime | None = None
    failure_count: int
    recovery_count: int
    state: str


class IncidentDetailResponse(IncidentResponse):
    monitor_url: str


class IncidentListResponse(BaseModel):
    items: list[IncidentResponse]
    page: int
    page_size: int
    total: int

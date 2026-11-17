"""Pydantic schemas for the dashboard endpoint (US-13)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DashboardMonitorItem(BaseModel):
    """Health summary for a single active monitor on the dashboard."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    status: str  # "healthy", "failing", "unknown"
    last_checked_at: datetime | None = None
    last_response_time_ms: int | None = None
    open_incident_id: UUID | None = None


class DashboardSummary(BaseModel):
    """Aggregate health counts for the caller's active monitors."""

    model_config = ConfigDict(from_attributes=True)

    total_monitors: int
    healthy: int
    failing: int
    unknown: int
    open_incidents: int


class DashboardResponse(BaseModel):
    """Response payload for GET /api/v1/dashboard."""

    model_config = ConfigDict(from_attributes=True)

    monitors: list[DashboardMonitorItem]
    summary: DashboardSummary

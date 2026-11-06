from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

ResultStatus = Literal["healthy", "failing"]


class HealthCheckResultResponse(BaseModel):
    """One persisted health-check result."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    monitor_id: UUID
    checked_at: datetime
    status: ResultStatus
    http_status_code: int | None = None
    response_time_ms: int | None = None
    timeout: bool
    connection_error: bool
    ssl_error: bool
    error_message: str | None = None
    response_body_excerpt: str | None = None
    created_at: datetime


class HealthCheckResultsResponse(BaseModel):
    """Paginated health-check results for a monitor."""

    items: list[HealthCheckResultResponse]
    page: int
    page_size: int
    total: int
    start_time: datetime
    end_time: datetime

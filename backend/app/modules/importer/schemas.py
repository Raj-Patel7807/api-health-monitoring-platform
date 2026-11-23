"""Pydantic schemas for API documentation endpoint extraction and import."""

from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.monitors.models import HttpMethod


class CandidateMonitor(BaseModel):
    """An endpoint discovered from API documentation ready for monitor creation."""

    name: str = Field(..., max_length=150)
    url: str
    method: HttpMethod = HttpMethod.GET
    expected_status_code: int = Field(default=200, ge=100, le=599)
    check_interval_seconds: int = Field(default=30, ge=10, le=86400)
    timeout_seconds: int = Field(default=10, ge=1, le=120)
    failure_threshold: int = Field(default=3, ge=1, le=20)
    recovery_threshold: int = Field(default=2, ge=1, le=20)
    description: str | None = None
    is_valid: bool = True
    validation_error: str | None = None


class ImportPreviewResponse(BaseModel):
    """Preview of endpoints discovered in the uploaded documentation file."""

    filename: str
    total_found: int
    valid_count: int
    items: list[CandidateMonitor]


class ImportCommitRequest(BaseModel):
    """Selected candidate monitors to be persisted to the database."""

    base_url: str | None = None
    items: list[CandidateMonitor]


class ImportCommitResponse(BaseModel):
    """Confirmation of imported monitors."""

    imported_count: int
    monitor_ids: list[UUID]

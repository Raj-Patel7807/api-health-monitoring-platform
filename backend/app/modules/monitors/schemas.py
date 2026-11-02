"""Pydantic schemas for Monitor CRUD and validation (US-02)."""

import enum
import urllib.parse
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError


class HttpMethod(enum.StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


def _validate_url_str(v: str) -> str:
    cleaned = v.strip()
    if not cleaned:
        raise PydanticCustomError("value_error", "URL cannot be empty.")
    if len(cleaned) > 2048:
        raise PydanticCustomError("value_error", "URL length cannot exceed 2048 characters.")
    parsed = urllib.parse.urlparse(cleaned)
    if parsed.scheme.lower() not in ("http", "https"):
        raise PydanticCustomError("value_error", "URL must have http or https scheme.")
    if not parsed.netloc:
        raise PydanticCustomError("value_error", "URL must have a valid host.")
    return cleaned


class MonitorBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    url: str = Field(..., max_length=2048)
    method: HttpMethod = HttpMethod.GET
    check_interval_seconds: int = Field(default=60, gt=0, le=86400)
    timeout_seconds: int = Field(default=10, gt=0, le=300)
    expected_status_code: int = Field(default=200, ge=100, le=599)
    failure_threshold: int = Field(default=3, gt=0, le=100)
    recovery_threshold: int = Field(default=2, gt=0, le=100)
    enabled: bool = True
    user_agent: str | None = Field(default="APIMonitor/1.0", max_length=255)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise PydanticCustomError("value_error", "Name cannot be empty or whitespace only.")
        return cleaned

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        return _validate_url_str(v)

    @field_validator("method", mode="before")
    @classmethod
    def normalize_method(cls, v: object) -> object:
        if isinstance(v, str):
            v_upper = v.strip().upper()
            try:
                return HttpMethod(v_upper)
            except ValueError:
                raise PydanticCustomError(
                    "value_error",
                    f"Invalid HTTP method: {v}. Must be one of {[m.value for m in HttpMethod]}",
                ) from None
        return v


class MonitorCreateRequest(MonitorBase):
    team_id: UUID | None = None

    @model_validator(mode="after")
    def validate_timeout_against_interval(self) -> "MonitorCreateRequest":
        if self.timeout_seconds > self.check_interval_seconds:
            raise PydanticCustomError(
                "value_error",
                (
                    f"timeout_seconds ({self.timeout_seconds}) cannot exceed "
                    f"check_interval_seconds ({self.check_interval_seconds})."
                ),
            )
        return self


class MonitorUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    url: str | None = Field(default=None, max_length=2048)
    method: HttpMethod | None = None
    enabled: bool | None = None
    check_interval_seconds: int | None = Field(default=None, gt=0, le=86400)
    timeout_seconds: int | None = Field(default=None, gt=0, le=300)
    expected_status_code: int | None = Field(default=None, ge=100, le=599)
    failure_threshold: int | None = Field(default=None, gt=0, le=100)
    recovery_threshold: int | None = Field(default=None, gt=0, le=100)
    user_agent: str | None = Field(default=None, max_length=255)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        if v is not None:
            cleaned = v.strip()
            if not cleaned:
                raise PydanticCustomError("value_error", "Name cannot be empty or whitespace only.")
            return cleaned
        return v

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str | None) -> str | None:
        if v is not None:
            return _validate_url_str(v)
        return v

    @field_validator("method", mode="before")
    @classmethod
    def normalize_method(cls, v: object) -> object:
        if v is not None and isinstance(v, str):
            v_upper = v.strip().upper()
            try:
                return HttpMethod(v_upper)
            except ValueError:
                raise PydanticCustomError(
                    "value_error",
                    f"Invalid HTTP method: {v}. Must be one of {[m.value for m in HttpMethod]}",
                ) from None
        return v

    @model_validator(mode="after")
    def validate_partial_timeout_against_interval(self) -> "MonitorUpdateRequest":
        if (
            self.timeout_seconds is not None
            and self.check_interval_seconds is not None
            and self.timeout_seconds > self.check_interval_seconds
        ):
            raise PydanticCustomError(
                "value_error",
                (
                    f"timeout_seconds ({self.timeout_seconds}) cannot exceed "
                    f"check_interval_seconds ({self.check_interval_seconds})."
                ),
            )
        return self


class MonitorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_id: UUID
    name: str
    url: str
    method: str
    enabled: bool
    check_interval_seconds: int
    timeout_seconds: int
    expected_status_code: int
    failure_threshold: int
    recovery_threshold: int
    user_agent: str | None = None
    created_at: datetime
    updated_at: datetime


class MonitorDetailResponse(MonitorResponse):
    current_interval_seconds: int
    consecutive_failures: int
    consecutive_successes: int
    next_check_at: datetime | None = None
    backoff_until: datetime | None = None


class MonitorListResponse(BaseModel):
    items: list[MonitorResponse]
    page: int
    page_size: int
    total: int

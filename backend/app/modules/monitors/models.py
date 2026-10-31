import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Enum, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, DateTimeUTC


class HttpMethod(enum.StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class Monitor(Base):
    """SQLAlchemy model for the monitors table."""

    __tablename__ = "monitors"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    team_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    method: Mapped[str] = mapped_column(
        Enum(
            HttpMethod,
            name="http_method",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=HttpMethod.GET.value,
        nullable=False,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    check_interval_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    current_interval_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    failure_threshold: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    recovery_threshold: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    consecutive_successes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    backoff_until: Mapped[datetime | None] = mapped_column(DateTimeUTC, nullable=True)
    expected_status_code: Mapped[int] = mapped_column(Integer, default=200, nullable=False)
    user_agent: Mapped[str | None] = mapped_column(
        String(255), default="APIMonitor/1.0", nullable=True
    )
    next_check_at: Mapped[datetime | None] = mapped_column(DateTimeUTC, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTimeUTC, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTimeUTC, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTimeUTC,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

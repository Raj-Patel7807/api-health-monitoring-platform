from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, DateTimeUTC


class Monitor(Base):
    """SQLAlchemy model for the monitors table."""

    __tablename__ = "monitors"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    team_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    method: Mapped[str] = mapped_column(String(10), default="GET", nullable=False)
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
    created_at: Mapped[datetime | None] = mapped_column(DateTimeUTC, default=None, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTimeUTC, default=None, nullable=True)

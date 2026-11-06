from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Enum, ForeignKey, Integer, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, DateTimeUTC


class HealthCheckResult(Base):
    """SQLAlchemy model for partitioned health check results."""

    __tablename__ = "health_check_results"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)

    checked_at: Mapped[datetime] = mapped_column(
        DateTimeUTC,
        primary_key=True,
        nullable=False,
    )

    monitor_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("monitors.id", ondelete="CASCADE"),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        Enum(
            "healthy",
            "failing",
            name="check_status",
            create_type=False,
        ),
        nullable=False,
    )

    http_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    timeout: Mapped[bool] = mapped_column(default=False, nullable=False)
    connection_error: Mapped[bool] = mapped_column(default=False, nullable=False)
    ssl_error: Mapped[bool] = mapped_column(default=False, nullable=False)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    response_body_excerpt: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTimeUTC,
        nullable=False,
        server_default=func.now(),
    )

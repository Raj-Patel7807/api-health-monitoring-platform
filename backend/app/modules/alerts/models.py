"""SQLAlchemy ORM model for alert_deliveries table (US-11 / B5)."""

import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Enum, ForeignKey, Integer, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, DateTimeUTC


class DeliveryStatus(enum.StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class DeliveryEventType(enum.StrEnum):
    OPENED = "opened"
    RESOLVED = "resolved"


class AlertDelivery(Base):
    """One alert delivery attempt per (incident, channel, event_type).

    The unique constraint (incident_id, notification_channel_id, event_type)
    provides the idempotency key — the Celery task will only send if status == 'pending'.
    Secrets are NEVER stored here; error_message must be sanitized before storage.
    """

    __tablename__ = "alert_deliveries"
    __table_args__ = (
        UniqueConstraint(
            "incident_id",
            "notification_channel_id",
            "event_type",
            name="uq_alert_deliveries_incident_channel_event",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    incident_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False
    )
    notification_channel_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("notification_channels.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(
        Enum(DeliveryEventType, name="delivery_event_type", create_type=False),
        nullable=False,
        default=DeliveryEventType.OPENED,
    )
    status: Mapped[str] = mapped_column(
        Enum(DeliveryStatus, name="delivery_status", create_type=False),
        nullable=False,
        default=DeliveryStatus.PENDING,
    )
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sent_at: Mapped[datetime | None] = mapped_column(DateTimeUTC, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTimeUTC, nullable=False, server_default=func.now()
    )

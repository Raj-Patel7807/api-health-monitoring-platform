"""SQLAlchemy ORM model for notification_channels (US-03)."""

import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Enum, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, DateTimeUTC


class ChannelType(enum.StrEnum):
    slack = "slack"
    discord = "discord"
    email = "email"
    webhook = "webhook"


class NotificationChannel(Base):
    """A notification target (Slack, Discord, email, or webhook) owned by a team.

    ``monitor_id=None`` means the channel applies to the whole team.
    The raw secret is **never** stored here — only a safe display hint.
    """

    __tablename__ = "notification_channels"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    team_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    monitor_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    type: Mapped[str] = mapped_column(
        Enum(ChannelType, name="channel_type", create_type=False),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Non-secret configuration options (no keys required currently).
    configuration: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    # Pointer to the secrets vault — never the raw secret value.
    secret_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Safe, truncated preview shown to users after creation (e.g. "hooks.slack.com/…/X7Q").
    secret_display_hint: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Soft-delete: alert_deliveries FK prevents hard deletes once deliveries exist.
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

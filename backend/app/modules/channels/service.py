"""Database service functions for notification channel lifecycle (US-03)."""

import json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.channels.models import NotificationChannel
from app.modules.channels.schemas import (
    ChannelCreateRequest,
    ChannelUpdateRequest,
    _make_display_hint,
)


async def create_channel(
    db: AsyncSession,
    team_id: UUID,
    data: ChannelCreateRequest,
) -> NotificationChannel:
    """Persist a new channel.  The raw secret is discarded; only the hint is kept."""
    now = datetime.now(UTC)
    hint = _make_display_hint(data.type, data.secret_value)
    channel = NotificationChannel(
        team_id=team_id,
        monitor_id=data.monitor_id,
        type=data.type.value,
        name=data.name,
        is_enabled=True,
        configuration=json.dumps(data.configuration),
        secret_display_hint=hint,
        created_at=now,
        updated_at=now,
    )
    db.add(channel)
    await db.flush()
    await db.refresh(channel)
    return channel


async def get_channel(
    db: AsyncSession,
    team_id: UUID,
    channel_id: UUID,
) -> NotificationChannel | None:
    """Return an active (non-soft-deleted) channel scoped to the team."""
    stmt = select(NotificationChannel).where(
        NotificationChannel.id == channel_id,
        NotificationChannel.team_id == team_id,
        NotificationChannel.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_channels(
    db: AsyncSession,
    team_id: UUID,
    monitor_id: UUID | None = None,
    scope_team_only: bool = False,
) -> list[NotificationChannel]:
    """Return active channels for a team, optionally filtered by monitor or scope.

    - monitor_id provided  → channels attached to that monitor only
    - scope_team_only=True → team-wide channels (monitor_id IS NULL) only
    - no filter            → all channels for the team
    """
    stmt = select(NotificationChannel).where(
        NotificationChannel.team_id == team_id,
        NotificationChannel.deleted_at.is_(None),
    )
    if monitor_id is not None:
        stmt = stmt.where(NotificationChannel.monitor_id == monitor_id)
    elif scope_team_only:
        stmt = stmt.where(NotificationChannel.monitor_id.is_(None))

    stmt = stmt.order_by(NotificationChannel.created_at.asc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_channel(
    db: AsyncSession,
    channel: NotificationChannel,
    data: ChannelUpdateRequest,
    channel_type_str: str,
) -> NotificationChannel:
    """Partially update a channel. Rotates secret_display_hint when secret_value is provided."""
    from app.modules.channels.models import ChannelType
    from app.modules.channels.schemas import _validate_secret

    if data.name is not None:
        channel.name = data.name
    if data.is_enabled is not None:
        channel.is_enabled = data.is_enabled
    if data.configuration is not None:
        channel.configuration = json.dumps(data.configuration)
    if data.secret_value is not None:
        # Validate new secret against the channel's original type (type cannot change).
        channel_type = ChannelType(channel_type_str)
        validated = _validate_secret(channel_type, data.secret_value)
        channel.secret_display_hint = _make_display_hint(channel_type, validated)
        # secret_ref intentionally not updated here — vault rotation is out of scope for MVP.

    channel.updated_at = datetime.now(UTC)
    await db.flush()
    await db.refresh(channel)
    return channel


async def soft_delete_channel(
    db: AsyncSession,
    channel: NotificationChannel,
) -> None:
    """Soft-delete a channel.

    Hard DELETE is not used because alert_deliveries holds an FK reference.
    Setting deleted_at hides the channel from lists and skips it in dispatchers.
    """
    now = datetime.now(UTC)
    channel.deleted_at = now
    channel.is_enabled = False
    channel.updated_at = now
    await db.flush()

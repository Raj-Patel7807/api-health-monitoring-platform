"""Alert dispatcher (B5): picks applicable channels, creates alert_deliveries rows,
and enqueues one Celery task per delivery.

Channel precedence (AC-03.4):
- If the monitor has its own channels (monitor_id = monitor.id, is_enabled, not deleted),
  use ONLY those.
- Otherwise fall back to team-wide channels (monitor_id IS NULL, is_enabled, not deleted).

Delivery rows are committed with incident transitions and claimed by the sending worker.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import ColumnElement, select
from sqlalchemy.orm import Session

from app.modules.alerts.models import AlertDelivery, DeliveryEventType, DeliveryStatus
from app.modules.channels.models import NotificationChannel


def pick_channels(session: Session, monitor_id: UUID, team_id: UUID) -> list[NotificationChannel]:
    """Return the notification channels applicable for this monitor.

    Precedence: monitor-specific channels first; falls back to team-wide when none.
    Skips disabled (is_enabled=False) and soft-deleted (deleted_at IS NOT NULL) channels.
    """
    # Try monitor-specific channels first
    monitor_channels: list[NotificationChannel] = list(
        session.execute(
            select(NotificationChannel).where(
                NotificationChannel.monitor_id == monitor_id,
                NotificationChannel.team_id == team_id,
                NotificationChannel.is_enabled.is_(True),
                NotificationChannel.deleted_at.is_(None),
            )
        ).scalars()
    )
    if monitor_channels:
        return monitor_channels

    # Fall back to team-wide channels (monitor_id IS NULL)
    team_channels: list[NotificationChannel] = list(
        session.execute(
            select(NotificationChannel).where(
                NotificationChannel.monitor_id.is_(None),
                NotificationChannel.team_id == team_id,
                NotificationChannel.is_enabled.is_(True),
                NotificationChannel.deleted_at.is_(None),
            )
        ).scalars()
    )
    return team_channels


def create_delivery_rows(
    session: Session,
    incident_id: UUID,
    channels: list[NotificationChannel],
    event_type: str,
) -> list[AlertDelivery]:
    """Create one alert_deliveries row per channel (idempotent via select-then-insert).

    Returns the list of AlertDelivery objects (newly created or pre-existing).
    """
    deliveries: list[AlertDelivery] = []
    for channel in channels:
        existing = session.execute(
            select(AlertDelivery).where(
                AlertDelivery.incident_id == incident_id,
                AlertDelivery.notification_channel_id == channel.id,
                AlertDelivery.event_type == event_type,
            )
        ).scalar_one_or_none()

        if existing is not None:
            deliveries.append(existing)
            continue

        delivery = AlertDelivery(
            incident_id=incident_id,
            notification_channel_id=channel.id,
            event_type=DeliveryEventType(event_type),
            status=DeliveryStatus.PENDING,
            attempt_count=0,
        )
        session.add(delivery)
        session.flush()
        deliveries.append(delivery)

    return deliveries


def publish_pending_deliveries(session: Session, *filters: ColumnElement[bool]) -> None:
    """Publish committed, unclaimed rows. Beat retries a failed publication."""
    from app.workers.tasks import send_alert_task

    ids = session.scalars(
        select(AlertDelivery.id).where(
            AlertDelivery.status == DeliveryStatus.PENDING,
            AlertDelivery.attempt_started_at.is_(None),
            *filters,
        )
    )
    for delivery_id in ids:
        send_alert_task.delay(str(delivery_id))

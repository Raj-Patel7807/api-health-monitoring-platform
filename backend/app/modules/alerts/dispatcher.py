"""Alert dispatcher (B5): picks applicable channels, creates alert_deliveries rows,
and enqueues one Celery task per delivery.

Channel precedence (AC-03.4):
- If the monitor has its own channels (monitor_id = monitor.id, is_enabled, not deleted),
  use ONLY those.
- Otherwise fall back to team-wide channels (monitor_id IS NULL, is_enabled, not deleted).

Exactly-once guarantee:
- One alert_deliveries row per (incident_id, channel_id, event_type), checked before insert.
- The Celery task checks status == 'pending' before sending (idempotent).
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.alerts.models import AlertDelivery, DeliveryEventType, DeliveryStatus
from app.modules.channels.models import NotificationChannel

logger = logging.getLogger(__name__)


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


def dispatch_alert(
    session: Session,
    incident_id: UUID,
    monitor_id: UUID,
    team_id: UUID,
    event_type: str,
) -> None:
    """Pick channels, create delivery rows, and enqueue Celery tasks.

    This is called from post-commit hooks so the rows must be committed before
    the task can be picked up.  We call session.commit() ourselves here if
    new rows were added, then enqueue the tasks.
    """
    from app.workers.tasks import send_alert_task

    channels = pick_channels(session, monitor_id, team_id)
    if not channels:
        logger.info(
            "dispatch_alert: no applicable channels for monitor %s / team %s", monitor_id, team_id
        )
        return

    deliveries = create_delivery_rows(session, incident_id, channels, event_type)

    # Flush + commit so tasks can read the rows
    try:
        session.commit()
    except Exception:
        session.rollback()
        logger.exception(
            "dispatch_alert: failed to commit delivery rows for incident %s", incident_id
        )
        return

    for delivery in deliveries:
        if delivery.status == DeliveryStatus.PENDING:
            try:
                send_alert_task.delay(str(delivery.id))
            except Exception:
                logger.exception(
                    "dispatch_alert: failed to enqueue send_alert_task for delivery %s",
                    delivery.id,
                )

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta

from kombu.exceptions import OperationalError as BrokerOperationalError  # type: ignore[import-untyped]
from redis.exceptions import ConnectionError as RedisConnectionError  # type: ignore[import-untyped]
from sqlalchemy import desc, select, text, update
from sqlalchemy.exc import OperationalError as DatabaseOperationalError

from app.db.session import get_db_session
from app.modules.monitors.scheduler import find_and_schedule_due_monitors
from app.workers.celery_app import celery_app
from celery import Task  # type: ignore[attr-defined]

logger = logging.getLogger(__name__)


@celery_app.task(  # type: ignore[misc]
    bind=True,
    name="app.workers.tasks.schedule_due_monitors",
    max_retries=3,
    autoretry_for=(
        DatabaseOperationalError,
        BrokerOperationalError,
        RedisConnectionError,
        ConnectionError,
        TimeoutError,
    ),
    retry_backoff=5,
    retry_backoff_max=60,
    retry_jitter=True,
)
def schedule_due_monitors(self: Task) -> list[str]:
    """Find due monitors and dispatch them with automatic exponential retries."""
    with get_db_session() as session:
        return find_and_schedule_due_monitors(session)  # type: ignore[return-value]


@celery_app.task(  # type: ignore[misc]
    bind=True,
    name="app.workers.tasks.ensure_next_month_partition",
    max_retries=3,
    autoretry_for=(DatabaseOperationalError,),
    retry_backoff=30,
    retry_backoff_max=300,
    retry_jitter=True,
)
def ensure_next_month_partition(self: Task) -> str:
    """Ensure that next month's health-check results partition exists."""
    with get_db_session() as session:
        session.execute(
            text(
                """
                SELECT create_health_check_partition(
                    (
                        date_trunc('month', CURRENT_DATE)
                        + INTERVAL '1 month'
                    )::date
                )
                """
            )
        )
        session.commit()

    logger.info("Verified next month's health-check results partition.")
    return "Next month's health-check results partition is ready."


@celery_app.task(  # type: ignore[misc]
    bind=True,
    name="app.workers.tasks.run_health_check",
    acks_late=True,
    reject_on_worker_lost=True,
    max_retries=3,
)
def run_health_check(self: Task, monitor_id: str, check_id: str | None = None) -> str:
    """Execute a health check for the given monitor."""
    from app.modules.monitors.checker import check_monitor_by_id

    try:
        check_monitor_by_id(monitor_id, check_id=check_id)
        return monitor_id
    except Exception as exc:
        logger.exception(
            "Unexpected error running health check for monitor %s",
            monitor_id,
        )
        raise self.retry(exc=exc, countdown=5) from exc  # type: ignore[attr-defined]


@celery_app.task(  # type: ignore[misc]
    bind=True,
    name="app.workers.tasks.dispatch_notification",
    max_retries=3,
    retry_backoff=True,
    retry_jitter=True,
)
def dispatch_notification(self: Task, delivery_id: str) -> str:
    """Reserve notification delivery work without contacting a provider yet."""
    return delivery_id


@celery_app.task(  # type: ignore[misc]
    bind=True,
    name="app.workers.tasks.analyze_incident",
    max_retries=2,
    retry_backoff=True,
)
def analyze_incident(self: Task, incident_id: str) -> str:
    """Reserve advisory AI work; it must not determine monitoring facts."""
    return incident_id


@celery_app.task(  # type: ignore[misc]
    bind=True,
    name="app.workers.tasks.send_alert_task",
    acks_late=True,
    reject_on_worker_lost=True,
    max_retries=0,
)
def send_alert_task(self: Task, delivery_id: str) -> str:
    """Send one alert delivery. Idempotent: skips if not pending.

    Security: the secret is decrypted inside the sender, never logged.
    A failed send sets status=failed, attempt_count=1, sanitized error_message.
    Other channels are not affected by this channel's failure.
    """
    from app.modules.alerts.models import AlertDelivery
    from app.modules.alerts.models import DeliveryStatus as AlertDeliveryStatus
    from app.modules.alerts.senders import AlertMessage, AlertSendError, get_sender
    from app.modules.channels.models import NotificationChannel
    from app.modules.incidents.models import Incident
    from app.modules.monitors.models import Monitor
    from app.modules.results.models import HealthCheckResult

    with get_db_session() as session:
        # Commit the exclusive claim before any provider can observe this delivery.
        claimed = session.scalar(
            update(AlertDelivery)
            .where(
                AlertDelivery.id == uuid.UUID(delivery_id),
                AlertDelivery.status == AlertDeliveryStatus.PENDING,
                AlertDelivery.attempt_started_at.is_(None),
            )
            .values(attempt_count=1, attempt_started_at=datetime.now(UTC))
            .returning(AlertDelivery.id)
        )
        session.commit()
        if claimed is None:
            return delivery_id
        delivery = session.get(AlertDelivery, claimed)
        if delivery is None:
            return delivery_id

        incident = session.get(Incident, delivery.incident_id)
        channel = session.get(NotificationChannel, delivery.notification_channel_id)

        if incident is None or channel is None:
            logger.error(
                "send_alert_task: incident or channel not found for delivery %s", delivery_id
            )
            delivery.status = AlertDeliveryStatus.FAILED
            delivery.error_message = "Incident or channel not found."
            session.commit()
            return delivery_id

        monitor = session.get(Monitor, incident.monitor_id)

        # Get the last result for failure_reason (opened alerts only)
        last_result = session.execute(
            select(HealthCheckResult)
            .where(HealthCheckResult.monitor_id == incident.monitor_id)
            .order_by(desc(HealthCheckResult.checked_at))
            .limit(1)
        ).scalar_one_or_none()
        failure_reason = last_result.error_message if last_result else None

        checked_at = (
            incident.opened_at
            if delivery.event_type == "opened"
            else (incident.resolved_at or incident.opened_at)
        )
        message = AlertMessage(
            monitor_name=monitor.name if monitor else "Unknown",
            monitor_url=monitor.url if monitor else "",
            event_type=str(delivery.event_type),
            checked_at=checked_at,
            failure_reason=failure_reason,
        )

        try:
            sender = get_sender(str(channel.type))
            sender.send(channel, message)
            # A delayed acknowledgement can arrive after recovery flagged the claim.
            session.execute(
                update(AlertDelivery)
                .where(AlertDelivery.id == claimed)
                .values(
                    status=AlertDeliveryStatus.SENT, sent_at=datetime.now(UTC), error_message=None
                )
            )
        except AlertSendError as exc:
            safe_msg = str(exc)[:500]
            delivery.status = AlertDeliveryStatus.FAILED
            delivery.error_message = safe_msg
            logger.error(
                "send_alert_task: delivery %s failed (AlertSendError): %s", delivery_id, safe_msg
            )
        except Exception as exc:
            safe_msg = f"{type(exc).__name__}: send failed"
            delivery.status = AlertDeliveryStatus.FAILED
            delivery.error_message = safe_msg
            logger.error("send_alert_task: delivery %s failed: %s", delivery_id, safe_msg)

        session.commit()
    return delivery_id


@celery_app.task(name="app.workers.tasks.recover_alert_deliveries")
def recover_alert_deliveries() -> None:
    from app.modules.alerts.dispatcher import publish_pending_deliveries
    from app.modules.alerts.models import AlertDelivery, DeliveryStatus

    now = datetime.now(UTC)
    with get_db_session() as session:
        # A provider may already have accepted a claimed message. Never replay
        # that call automatically when its worker disappears.
        session.execute(
            update(AlertDelivery)
            .where(
                AlertDelivery.status == DeliveryStatus.PENDING,
                AlertDelivery.attempt_started_at < now - timedelta(minutes=5),
            )
            .values(
                status=DeliveryStatus.FAILED,
                error_message="Worker interrupted. Provider delivery outcome is unknown.",
            )
        )
        session.commit()
        publish_pending_deliveries(session, AlertDelivery.created_at < now - timedelta(seconds=30))

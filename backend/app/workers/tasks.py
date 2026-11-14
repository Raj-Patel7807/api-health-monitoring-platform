from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from kombu.exceptions import OperationalError as BrokerOperationalError  # type: ignore[import-untyped]
from redis.exceptions import ConnectionError as RedisConnectionError  # type: ignore[import-untyped]
from sqlalchemy import desc, select, text
from sqlalchemy.exc import OperationalError as DatabaseOperationalError
from sqlalchemy.orm import sessionmaker

from app.db.session import create_database_engine, get_db_session
from app.models.delivery import DeliveryLog, DeliveryStatus
from app.modules.monitors.scheduler import find_and_schedule_due_monitors
from app.services.email_sender import send_email
from app.services.webhook_sender import send_webhook
from app.workers.celery_app import celery_app
from celery import Task  # type: ignore[import-untyped]

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
def run_health_check(self: Task, monitor_id: str) -> str:
    """Execute a health check for the given monitor."""
    from app.modules.monitors.checker import check_monitor_by_id

    try:
        check_monitor_by_id(monitor_id)
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


@celery_app.task(name="app.workers.tasks.send_email_task")  # type: ignore[misc]
def send_email_task(delivery_id: str) -> str:
    """Celery task to send an email based on a DeliveryLog record."""
    db_engine = create_database_engine()
    SessionLocal = sessionmaker(bind=db_engine)
    db = SessionLocal()
    delivery = db.query(DeliveryLog).filter(DeliveryLog.id == uuid.UUID(delivery_id)).first()
    if not delivery:
        raise ValueError(f"Delivery {delivery_id} not found")
    payload: dict[str, Any] = dict(delivery.request_payload) if delivery.request_payload else {}
    to: str = str(payload.get("to", ""))
    subject: str = str(payload.get("subject", ""))
    template_name: str = str(payload.get("template_name", "default.html"))
    context: dict[str, Any] = payload.get("context", {})
    result = asyncio.get_event_loop().run_until_complete(
        send_email(
            to=to,
            subject=subject,
            template_name=template_name,
            context=context,
        )
    )
    if result:
        delivery.update_status(DeliveryStatus.success)
    else:
        delivery.update_status(DeliveryStatus.failed)
    db.commit()
    db.close()
    return delivery_id


@celery_app.task(name="app.workers.tasks.send_webhook_task")  # type: ignore[misc]
def send_webhook_task(delivery_id: str) -> str:
    """Celery task to send a webhook based on a DeliveryLog record."""
    db_engine = create_database_engine()
    SessionLocal = sessionmaker(bind=db_engine)
    db = SessionLocal()
    delivery = db.query(DeliveryLog).filter(DeliveryLog.id == uuid.UUID(delivery_id)).first()
    if not delivery:
        raise ValueError(f"Delivery {delivery_id} not found")
    payload: dict[str, Any] = dict(delivery.request_payload) if delivery.request_payload else {}
    url: str = str(payload.get("url", ""))
    event_type: str = str(payload.get("event_type", "unknown"))
    body: dict[str, Any] = payload.get("payload", {})
    asyncio.get_event_loop().run_until_complete(
        send_webhook(url=url, payload={"event_type": event_type, **body})
    )
    delivery.update_status(DeliveryStatus.success)
    db.commit()
    db.close()
    return delivery_id


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
        delivery = session.get(AlertDelivery, uuid.UUID(delivery_id))
        if delivery is None:
            logger.warning("send_alert_task: delivery %s not found", delivery_id)
            return delivery_id

        # Idempotency: only send if still pending
        if delivery.status != AlertDeliveryStatus.PENDING:
            logger.info(
                "send_alert_task: delivery %s already %s, skipping",
                delivery_id,
                delivery.status,
            )
            return delivery_id

        incident = session.get(Incident, delivery.incident_id)
        channel = session.get(NotificationChannel, delivery.notification_channel_id)

        if incident is None or channel is None:
            logger.error(
                "send_alert_task: incident or channel not found for delivery %s", delivery_id
            )
            delivery.status = AlertDeliveryStatus.FAILED
            delivery.attempt_count = 1
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
            delivery.status = AlertDeliveryStatus.SENT
            delivery.attempt_count = 1
            delivery.sent_at = datetime.now(UTC)
        except AlertSendError as exc:
            safe_msg = str(exc)[:500]
            delivery.status = AlertDeliveryStatus.FAILED
            delivery.attempt_count = 1
            delivery.error_message = safe_msg
            logger.error(
                "send_alert_task: delivery %s failed (AlertSendError): %s", delivery_id, safe_msg
            )
        except Exception as exc:
            safe_msg = f"{type(exc).__name__}: send failed"
            delivery.status = AlertDeliveryStatus.FAILED
            delivery.attempt_count = 1
            delivery.error_message = safe_msg
            logger.error("send_alert_task: delivery %s failed: %s", delivery_id, safe_msg)

        session.commit()
    return delivery_id


@celery_app.task(name="app.workers.tasks.replay_delivery_task")  # type: ignore[misc]
def replay_delivery_task(delivery_id: str) -> str:
    """Re-dispatch a delivery by its id (email or webhook)."""
    db_engine = create_database_engine()
    SessionLocal = sessionmaker(bind=db_engine)
    db = SessionLocal()
    delivery = db.query(DeliveryLog).filter(DeliveryLog.id == uuid.UUID(delivery_id)).first()
    if not delivery:
        raise ValueError(f"Delivery {delivery_id} not found")
    channel = str(delivery.channel_type)
    db.close()
    if "email" in channel:
        send_email_task.delay(delivery_id)
    else:
        send_webhook_task.delay(delivery_id)
    return delivery_id

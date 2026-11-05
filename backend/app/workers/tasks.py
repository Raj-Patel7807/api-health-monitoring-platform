from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from celery import Task  # type: ignore[import-untyped]
from kombu.exceptions import OperationalError as BrokerOperationalError  # type: ignore[import-untyped]
from redis.exceptions import ConnectionError as RedisConnectionError  # type: ignore[import-untyped]
from sqlalchemy import text
from sqlalchemy.exc import OperationalError as DatabaseOperationalError
from sqlalchemy.orm import sessionmaker

from app.db.session import create_database_engine, get_db_session
from app.models.delivery import DeliveryLog, DeliveryStatus
from app.modules.monitors.scheduler import find_and_schedule_due_monitors
from app.services.email_sender import send_email
from app.services.webhook_sender import send_webhook
from app.workers.celery_app import celery_app

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

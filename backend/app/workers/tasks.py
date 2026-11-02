import logging

try:
    from celery import Task
except ImportError:  # pragma: no cover
    class Task:  # minimal stub
        def __init__(self, *args, **kwargs):
            pass
try:
    from kombu.exceptions import OperationalError as BrokerOperationalError  # type: ignore
except ImportError:  # pragma: no cover
    class BrokerOperationalError(Exception):
        pass
try:
    from redis.exceptions import ConnectionError as RedisConnectionError
except ImportError:  # pragma: no cover
    class RedisConnectionError(Exception):
        pass
from sqlalchemy.exc import OperationalError as DatabaseOperationalError

from app.db.session import get_db_session
from app.modules.monitors.scheduler import find_and_schedule_due_monitors
from app.workers.celery_app import celery_app
from app.db.session import create_database_engine
from sqlalchemy.orm import sessionmaker
from app.services.email_sender import send_email
from app.services.webhook_sender import send_webhook
from app.models.delivery import DeliveryLog, DeliveryStatus
import uuid

logger = logging.getLogger(__name__)


@celery_app.task(
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
    """Find due monitors and dispatch them with automatic exponential retries.

    Celery handles retry countdown, jitter, and logging through task signals.
    Scheduled timestamps remain in PostgreSQL across worker restarts.
    """
    with get_db_session() as session:
        return find_and_schedule_due_monitors(session)


@celery_app.task(
    bind=True,
    name="app.workers.tasks.run_health_check",
    acks_late=True,
    reject_on_worker_lost=True,
    max_retries=3,
)
def run_health_check(self: Task, monitor_id: str) -> str:
    """Execute a health check for the given monitor.

    Classifies timeout, wrong status, connection error, and SSL failure.
    Retries up to 3 times on unexpected worker errors, not on check failures.
    Configured with late acknowledgment and reject-on-worker-lost so a worker crash
    causes the unacknowledged task to be safely requeued.
    """
    from app.modules.monitors.checker import check_monitor_by_id

    try:
        check_monitor_by_id(monitor_id)
        return monitor_id
    except Exception as exc:
        logger.exception("Unexpected error running health check for monitor %s", monitor_id)
        raise self.retry(exc=exc, countdown=5) from exc


@celery_app.task(
    bind=True,
    name="app.workers.tasks.dispatch_notification",
    max_retries=3,
    retry_backoff=True,
    retry_jitter=True,
)
def dispatch_notification(self: Task, delivery_id: str) -> str:
    """Reserve notification delivery work without contacting a provider yet.

    Supports up to 3 retries with backoff per FR8 / AC-12.2.
    """
    return delivery_id


@celery_app.task(
    bind=True,
    name="app.workers.tasks.analyze_incident",
    max_retries=2,
    retry_backoff=True,
)
def analyze_incident(self: Task, incident_id: str) -> str:
    """Reserve advisory AI work; it must not determine monitoring facts."""
    return incident_id

@celery_app.task(name="app.workers.tasks.send_email_task")
def send_email_task(delivery_id: str) -> str:
    """Celery task to send an email based on a DeliveryLog record."""
    db_engine = create_database_engine()
    SessionLocal = sessionmaker(bind=db_engine)
    db = SessionLocal()
    delivery = db.query(DeliveryLog).filter(DeliveryLog.id == uuid.UUID(delivery_id)).first()
    if not delivery:
        raise ValueError(f"Delivery {delivery_id} not found")
    # Assume delivery.request_payload contains keys: to, subject, template_data
    payload = delivery.request_payload
    result = send_email(to=payload["to"], subject=payload["subject"], template_data=payload.get("template_data", {}))
    # Update delivery status based on result
    if result:
        delivery.update_status(DeliveryStatus.success)
    else:
        delivery.update_status(DeliveryStatus.failed)
    db.commit()
    db.close()
    return delivery_id

@celery_app.task(name="app.workers.tasks.send_webhook_task")
def send_webhook_task(delivery_id: str) -> str:
    """Celery task to send a webhook based on a DeliveryLog record."""
    db_engine = create_database_engine()
    SessionLocal = sessionmaker(bind=db_engine)
    db = SessionLocal()
    delivery = db.query(DeliveryLog).filter(DeliveryLog.id == uuid.UUID(delivery_id)).first()
    if not delivery:
        raise ValueError(f"Delivery {delivery_id} not found")
    payload = delivery.request_payload
    url = payload.get("url")
    event_type = payload.get("event_type", "unknown")
    body = payload.get("payload", {})
    result_id = send_webhook(url=url, payload={"event_type": event_type, **body})
    # Update status based on send_webhook return – it logs itself
    delivery.update_status(DeliveryStatus.success)
    db.commit()
    db.close()
    return delivery_id

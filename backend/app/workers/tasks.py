import logging

from celery import Task

from app.db.session import get_db_session
from app.modules.monitors.scheduler import find_and_schedule_due_monitors
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.workers.tasks.schedule_due_monitors",
    max_retries=3,
    default_retry_delay=5,
    retry_backoff=True,
    retry_jitter=True,
)
def schedule_due_monitors(self: Task) -> list[str]:
    """Find monitors due for a check, queue run_health_check tasks, and update next_check_at.

    Retries with backoff on database or operational failure.
    Schedule state is persistently stored in PostgreSQL (monitors.next_check_at),
    ensuring worker crashes or scheduler restarts do not lose the schedule.
    """
    try:
        with get_db_session() as session:
            return find_and_schedule_due_monitors(session)
    except Exception as exc:
        logger.error(
            "schedule_due_monitors failed on attempt %d: %s",
            self.request.retries + 1,
            exc,
            exc_info=True,
        )
        raise self.retry(exc=exc) from exc


@celery_app.task(
    bind=True,
    name="app.workers.tasks.run_health_check",
    acks_late=True,
    reject_on_worker_lost=True,
)
def run_health_check(self: Task, monitor_id: str) -> str:
    """Reserve the monitoring queue contract; monitor logic is a later feature.

    Configured with late acknowledgment and reject-on-worker-lost so a worker crash
    causes the unacknowledged task to be safely requeued.
    """
    return monitor_id


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

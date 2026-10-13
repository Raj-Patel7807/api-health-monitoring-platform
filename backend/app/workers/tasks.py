from app.db.session import get_db_session
from app.modules.monitors.scheduler import find_and_schedule_due_monitors
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.tasks.schedule_due_monitors")
def schedule_due_monitors() -> list[str]:
    """Find monitors due for a check, queue run_health_check tasks, and update next_check_at."""
    with get_db_session() as session:
        return find_and_schedule_due_monitors(session)


@celery_app.task(name="app.workers.tasks.run_health_check")
def run_health_check(monitor_id: str) -> str:
    """Reserve the monitoring queue contract; monitor logic is a later feature."""

    return monitor_id


@celery_app.task(name="app.workers.tasks.dispatch_notification")
def dispatch_notification(delivery_id: str) -> str:
    """Reserve notification delivery work without contacting a provider yet."""

    return delivery_id


@celery_app.task(name="app.workers.tasks.analyze_incident")
def analyze_incident(incident_id: str) -> str:
    """Reserve advisory AI work; it must not determine monitoring facts."""

    return incident_id

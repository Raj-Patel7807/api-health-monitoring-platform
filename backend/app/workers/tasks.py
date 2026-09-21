from app.workers.celery_app import celery_app


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

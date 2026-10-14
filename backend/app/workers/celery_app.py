from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "api_health_monitor",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks", "app.workers.signals"],
)

# Queue topology
celery_app.conf.task_default_queue = "maintenance"
celery_app.conf.task_routes = {
    "app.workers.tasks.run_health_check": {"queue": "monitoring"},
    "app.workers.tasks.dispatch_notification": {"queue": "notifications"},
    "app.workers.tasks.analyze_incident": {"queue": "ai"},
    "app.workers.tasks.schedule_due_monitors": {"queue": "maintenance"},
}

# Worker resilience, crash safety, and acknowledgment
# task_acks_late ensures tasks are acknowledged only after completion
celery_app.conf.task_acks_late = True
# task_reject_on_worker_lost ensures that if a worker process crashes or is killed,
# the task is rejected back to the broker and requeued rather than lost
celery_app.conf.task_reject_on_worker_lost = True
# worker_prefetch_multiplier=1 prevents a worker from hoarding tasks
# that could be delayed if the worker crashes
celery_app.conf.worker_prefetch_multiplier = 1

# Observability and result backend configuration
celery_app.conf.task_track_started = True
celery_app.conf.result_extended = True
celery_app.conf.result_expires = 86400

# Serialization and timezone standards (UTC)
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.timezone = "UTC"
celery_app.conf.enable_utc = True

# Continuous beat schedule for monitoring loop
celery_app.conf.beat_schedule = {
    "schedule-due-monitors-every-10s": {
        "task": "app.workers.tasks.schedule_due_monitors",
        "schedule": 10.0,
    },
}

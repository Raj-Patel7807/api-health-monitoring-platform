from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "api_health_monitor",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)
celery_app.conf.task_default_queue = "maintenance"
celery_app.conf.task_routes = {
    "app.workers.tasks.run_health_check": {"queue": "monitoring"},
    "app.workers.tasks.dispatch_notification": {"queue": "notifications"},
    "app.workers.tasks.analyze_incident": {"queue": "ai"},
}
celery_app.conf.beat_schedule = {}

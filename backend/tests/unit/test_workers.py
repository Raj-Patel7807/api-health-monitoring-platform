from app.workers.celery_app import celery_app
from app.workers.tasks import analyze_incident, dispatch_notification, run_health_check


def test_worker_routes_keep_monitoring_and_side_effects_separate() -> None:
    assert celery_app.conf.task_routes["app.workers.tasks.run_health_check"] == {
        "queue": "monitoring"
    }
    assert celery_app.conf.task_routes["app.workers.tasks.dispatch_notification"] == {
        "queue": "notifications"
    }
    assert celery_app.conf.task_routes["app.workers.tasks.analyze_incident"] == {"queue": "ai"}


def test_foundation_tasks_do_not_call_external_services() -> None:
    assert run_health_check.run("monitor-1") == "monitor-1"
    assert dispatch_notification.run("delivery-1") == "delivery-1"
    assert analyze_incident.run("incident-1") == "incident-1"

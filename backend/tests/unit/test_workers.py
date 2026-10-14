import logging
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from app.workers.celery_app import celery_app
from app.workers.failure import (
    TaskFailureTracker,
    get_failed_task,
    get_failure_tracker,
    list_failed_tasks,
    record_failed_task,
    sanitize_payload,
)
from app.workers.signals import handle_task_failure, handle_task_retry
from app.workers.tasks import (
    analyze_incident,
    dispatch_notification,
    run_health_check,
    schedule_due_monitors,
)


def test_worker_routes_keep_monitoring_and_side_effects_separate() -> None:
    assert celery_app.conf.task_routes["app.workers.tasks.run_health_check"] == {
        "queue": "monitoring"
    }
    assert celery_app.conf.task_routes["app.workers.tasks.dispatch_notification"] == {
        "queue": "notifications"
    }
    assert celery_app.conf.task_routes["app.workers.tasks.analyze_incident"] == {"queue": "ai"}
    assert celery_app.conf.task_routes["app.workers.tasks.schedule_due_monitors"] == {
        "queue": "maintenance"
    }


def test_celery_worker_crash_safety_and_plumbing_configuration() -> None:
    # Acks late ensures tasks are acknowledged only after completion
    assert celery_app.conf.task_acks_late is True
    # Rejects and requeues task if worker process is lost/crashes
    assert celery_app.conf.task_reject_on_worker_lost is True
    # Prefetch multiplier of 1 prevents hoarding unacknowledged tasks
    assert celery_app.conf.worker_prefetch_multiplier == 1
    # Started task tracking for observability
    assert celery_app.conf.task_track_started is True
    # Result extended metadata and UTC timezone
    assert celery_app.conf.result_extended is True
    assert celery_app.conf.result_expires == 86400
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.result_serializer == "json"
    assert celery_app.conf.accept_content == ["json"]
    assert celery_app.conf.timezone == "UTC"
    assert celery_app.conf.enable_utc is True


def test_foundation_tasks_do_not_call_external_services() -> None:
    assert run_health_check.run("monitor-1") == "monitor-1"
    assert dispatch_notification.run("delivery-1") == "delivery-1"
    assert analyze_incident.run("incident-1") == "incident-1"


def test_task_retry_and_crash_settings_on_tasks() -> None:
    # schedule_due_monitors retry policy
    assert schedule_due_monitors.max_retries == 3
    assert schedule_due_monitors.retry_backoff == 5
    assert schedule_due_monitors.retry_jitter is True

    # run_health_check crash resilience
    assert run_health_check.acks_late is True
    assert run_health_check.reject_on_worker_lost is True

    # dispatch_notification retry policy (AC-12.2 / FR8)
    assert dispatch_notification.max_retries == 3
    assert dispatch_notification.retry_backoff is True
    assert dispatch_notification.retry_jitter is True

    # analyze_incident retry policy
    assert analyze_incident.max_retries == 2
    assert analyze_incident.retry_backoff is True


def test_schedule_due_monitors_retries_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    from unittest.mock import patch

    monkeypatch.setattr(
        "app.workers.tasks.get_db_session",
        MagicMock(side_effect=ConnectionRefusedError("Database unreachable")),
    )
    with patch.object(
        schedule_due_monitors, "retry", side_effect=RuntimeError("Retried!")
    ) as mock_retry:
        with pytest.raises(RuntimeError, match="Retried!"):
            schedule_due_monitors.apply(throw=True)
        mock_retry.assert_called_once()


def test_sanitize_payload_redacts_sensitive_keys() -> None:
    raw_data = {
        "username": "alice",
        "password": "supersecretpassword",
        "api_key": "12345-abcde",
        "auth_token": "bearer xyz",
        "nested": {
            "webhook_url": "https://hooks.slack.com/services/123",
            "normal_field": "ok_value",
        },
        "list_items": [
            {"secret_field": "hidden", "public_field": "visible"},
            "plain_text",
        ],
    }

    sanitized = sanitize_payload(raw_data)
    assert sanitized["username"] == "alice"
    assert sanitized["password"] == "[REDACTED]"
    assert sanitized["api_key"] == "[REDACTED]"
    assert sanitized["auth_token"] == "[REDACTED]"
    assert sanitized["nested"]["webhook_url"] == "[REDACTED]"
    assert sanitized["nested"]["normal_field"] == "ok_value"
    assert sanitized["list_items"][0]["secret_field"] == "[REDACTED]"
    assert sanitized["list_items"][0]["public_field"] == "visible"
    assert sanitized["list_items"][1] == "plain_text"


def test_task_failure_recording_and_retrieval() -> None:
    tracker = TaskFailureTracker(max_entries=5)
    now = datetime(2026, 10, 14, 10, 0, 0, tzinfo=UTC)

    err = ValueError("Test job crash")
    rec = tracker.record_failure(
        task_id="task-123",
        task_name="app.workers.tasks.run_health_check",
        exception=err,
        args=["monitor-456"],
        kwargs={"token": "secret"},
        traceback="Traceback...",
        worker="celery@worker-1",
        retries=2,
        now=now,
    )

    assert rec.task_id == "task-123"
    assert rec.task_name == "app.workers.tasks.run_health_check"
    assert rec.exception_type == "ValueError"
    assert rec.exception_message == "[REDACTED]"
    assert rec.args == ["[REDACTED]"]
    assert rec.kwargs == {"token": "[REDACTED]"}
    assert rec.traceback is None
    assert rec.worker == "celery@worker-1"
    assert rec.retries == 2
    assert rec.failed_at == now

    # to_dict verification
    data = rec.to_dict()
    assert data["task_id"] == "task-123"
    assert data["failed_at"] == "2026-10-14T10:00:00+00:00"

    # Retrieval
    retrieved = tracker.get_failure("task-123")
    assert retrieved is rec

    assert tracker.get_failure("non-existent") is None


def test_task_failure_tracker_eviction_and_order() -> None:
    tracker = TaskFailureTracker(max_entries=3)
    for i in range(5):
        tracker.record_failure(
            task_id=f"task-{i}",
            task_name="app.workers.tasks.run_health_check",
            exception=RuntimeError(f"Error {i}"),
        )

    # Only 3 entries should remain
    failures = tracker.list_failures(limit=10)
    assert len(failures) == 3
    # In reverse chronological order: task-4, task-3, task-2
    assert [f.task_id for f in failures] == ["task-4", "task-3", "task-2"]
    assert tracker.get_failure("task-0") is None
    assert tracker.get_failure("task-1") is None

    # Overwrite existing task_id
    tracker.record_failure(
        task_id="task-3",
        task_name="app.workers.tasks.run_health_check",
        exception=RuntimeError("Updated error"),
    )
    updated_failures = tracker.list_failures()
    assert [f.task_id for f in updated_failures] == ["task-3", "task-4", "task-2"]

    # Clear
    tracker.clear()
    assert tracker.list_failures() == []


def test_global_failure_helpers_and_signal_integration(caplog: pytest.LogCaptureFixture) -> None:
    tracker = get_failure_tracker()
    tracker.clear()

    # Test record_failed_task helper
    exc = ZeroDivisionError("division by zero")
    with caplog.at_level(logging.ERROR):
        rec = record_failed_task(
            task_id="signal-task-1",
            task_name="app.workers.tasks.schedule_due_monitors",
            exception=exc,
            args=[1, 2],
            kwargs={"auth_token": "secret123"},
            traceback="Traceback: line 10",
        )

    assert rec.task_id == "signal-task-1"
    assert get_failed_task("signal-task-1") is rec
    assert len(list_failed_tasks()) == 1
    assert "Recorded failed worker task" in caplog.text

    # Test handle_task_failure signal handler directly
    mock_sender = MagicMock()
    mock_sender.name = "app.workers.tasks.run_health_check"
    mock_sender.request.retries = 1
    mock_sender.request.hostname = "celery@host-1"

    handle_task_failure(
        sender=mock_sender,
        task_id="signal-task-2",
        exception=RuntimeError("Network timeout"),
        args=("monitor-abc",),
        kwargs={"timeout": 10},
        einfo="Traceback einfo",
    )

    failure_2 = get_failed_task("signal-task-2")
    assert failure_2 is not None
    assert failure_2.task_name == "app.workers.tasks.run_health_check"
    assert failure_2.exception_type == "RuntimeError"
    assert failure_2.retries == 1
    assert failure_2.worker == "celery@host-1"


def test_handle_task_failure_handles_missing_attributes() -> None:
    # No task_id or exception -> no-op
    handle_task_failure(sender=None, task_id=None, exception=None)
    assert get_failed_task("nonexistent") is None

    # Sender as a simple string without request attribute
    handle_task_failure(
        sender="raw_task_string",
        task_id="signal-task-raw",
        exception=ValueError("Raw sender failure"),
    )
    rec = get_failed_task("signal-task-raw")
    assert rec is not None
    assert rec.task_name == "raw_task_string"
    assert rec.worker is None
    assert rec.retries == 0


def test_handle_task_retry_logs_warning(caplog: pytest.LogCaptureFixture) -> None:
    mock_sender = MagicMock()
    mock_sender.name = "app.workers.tasks.dispatch_notification"
    mock_sender.request.retries = 2
    mock_sender.max_retries = 3

    with caplog.at_level(logging.WARNING):
        handle_task_retry(
            sender=mock_sender,
            task_id="retry-task-1",
            reason=ConnectionError("Third-party API down"),
        )

    assert (
        "Celery task retrying: app.workers.tasks.dispatch_notification[retry-task-1]" in caplog.text
    )
    assert "attempt=2 max_retries=3" in caplog.text


def test_scheduler_uses_exponential_retry_countdown(monkeypatch: pytest.MonkeyPatch) -> None:
    from unittest.mock import patch

    monkeypatch.setattr(
        "app.workers.tasks.get_db_session",
        MagicMock(side_effect=ConnectionRefusedError("Database unavailable")),
    )
    # Mock the exponential backoff calculator, and verify its result is passed
    # into Celery retry. The original code retried at a constant five seconds.
    with (
        patch("celery.app.autoretry.get_exponential_backoff_interval", return_value=10) as backoff,
        patch.object(schedule_due_monitors, "retry", side_effect=RuntimeError("Retried!")) as retry,
        pytest.raises(RuntimeError, match="Retried!"),
    ):
        schedule_due_monitors.apply(throw=True)

    assert backoff.call_args.kwargs["factor"] == 5
    assert backoff.call_args.kwargs["maximum"] == 60
    assert backoff.call_args.kwargs["full_jitter"] is True
    assert retry.call_args.kwargs["countdown"] == 10


def test_sensitive_failure_details_never_enter_custom_logs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    tracker = TaskFailureTracker()
    secret = "private-token-should-never-be-logged"
    with caplog.at_level(logging.ERROR):
        record = tracker.record_failure(
            task_id="sensitive-failure-1",
            task_name="app.workers.tasks.run_health_check",
            exception=RuntimeError(f"authentication token: {secret}"),
            args=[secret],
            kwargs={"notes": secret, "password": secret},
            traceback=f"Traceback containing {secret}",
        )
    assert record.exception_type == "RuntimeError"
    assert record.exception_message == "[REDACTED]"
    assert record.args == ["[REDACTED]"]
    assert record.kwargs == {"notes": "[REDACTED]", "password": "[REDACTED]"}
    assert record.traceback is None
    assert secret not in str(record.to_dict())
    assert secret not in caplog.text


def test_retry_signal_never_logs_sensitive_reason(caplog: pytest.LogCaptureFixture) -> None:
    sender = MagicMock()
    sender.name = "app.workers.tasks.schedule_due_monitors"
    sender.request.retries = 1
    sender.max_retries = 3
    secret = "private-token-should-never-be-logged"
    with caplog.at_level(logging.WARNING):
        handle_task_retry(
            sender=sender,
            task_id="retry-safe-1",
            reason=RuntimeError(f"credential={secret}"),
        )
    assert "reason_type=RuntimeError" in caplog.text
    assert secret not in caplog.text


def test_failure_signal_redacts_traceback_and_unknown_parameter_values(
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret = "private-token-should-never-be-logged"
    sender = MagicMock()
    sender.name = "app.workers.tasks.run_health_check"
    sender.request.retries = 2
    sender.request.hostname = "celery@test-worker"
    with caplog.at_level(logging.ERROR):
        handle_task_failure(
            sender=sender,
            task_id="failure-safe-1",
            exception=RuntimeError(f"secret={secret}"),
            args=(secret,),
            kwargs={"notes": secret},
            einfo=f"sensitive traceback: {secret}",
        )
    record = get_failed_task("failure-safe-1")
    assert record is not None
    assert record.traceback is None
    assert record.exception_message == "[REDACTED]"
    assert secret not in str(record.to_dict())
    assert secret not in caplog.text

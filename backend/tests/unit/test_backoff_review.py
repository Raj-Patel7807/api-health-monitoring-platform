"""Regression tests for recovery scheduling and short monitor intervals (PR #44)."""

from datetime import UTC, datetime, timedelta

from app.modules.monitors.backoff import (
    apply_failure_backoff,
    reset_monitor_backoff,
    update_monitor_backoff,
)
from app.modules.monitors.models import Monitor


def test_short_interval_uses_user_setting_instead_of_sixty_seconds() -> None:
    monitor = Monitor(check_interval_seconds=5, consecutive_failures=1)
    now = datetime(2026, 10, 14, 12, 0, tzinfo=UTC)

    assert apply_failure_backoff(monitor, now=now) == 10
    assert monitor.current_interval_seconds == 10
    assert monitor.backoff_until == now + timedelta(seconds=10)


def test_recovery_replaces_old_backoff_schedule() -> None:
    now = datetime(2026, 10, 14, 12, 0, tzinfo=UTC)
    monitor = Monitor(
        check_interval_seconds=60,
        current_interval_seconds=480,
        next_check_at=now + timedelta(seconds=480),
        backoff_until=now + timedelta(seconds=480),
    )

    reset_monitor_backoff(monitor, now=now)

    assert monitor.current_interval_seconds == 60
    assert monitor.backoff_until is None
    assert monitor.next_check_at == now + timedelta(seconds=60)


def test_healthy_update_propagates_recovery_time() -> None:
    now = datetime(2026, 10, 14, 12, 0, tzinfo=UTC)
    monitor = Monitor(
        check_interval_seconds=30,
        current_interval_seconds=240,
        next_check_at=now + timedelta(seconds=240),
        backoff_until=now + timedelta(seconds=240),
    )

    update_monitor_backoff(monitor, is_healthy=True, now=now)

    assert monitor.current_interval_seconds == 30
    assert monitor.backoff_until is None
    assert monitor.next_check_at == now + timedelta(seconds=30)

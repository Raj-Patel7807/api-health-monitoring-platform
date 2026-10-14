"""Exponential backoff and rate-limiting logic for failing monitors (US-16).

Implements AC-16.1 through AC-16.6 and DR4:
- AC-16.3 / DR4: A failing monitor applies exponential backoff instead of
  continually probing external endpoints at the normal frequency.
- AC-16.4: Enforces reasonable intervals and prevents overloading targets.
- AC-16.5: Identifies monitoring traffic with the standard platform User-Agent.
"""

from datetime import UTC, datetime, timedelta

from app.modules.monitors.models import Monitor

DEFAULT_USER_AGENT = "APIMonitor/1.0"
MAX_BACKOFF_INTERVAL_SECONDS = 86400  # 24 hours (matches max interval in schemas.py)
MIN_BACKOFF_INTERVAL_SECONDS = 10  # Matches DB schema check constraint (>= 10)
MAX_EXPONENT = 20  # Prevent integer overflow on astronomical consecutive failure counts


def calculate_exponential_backoff(
    base_interval_seconds: int,
    consecutive_failures: int,
    max_interval_seconds: int = MAX_BACKOFF_INTERVAL_SECONDS,
) -> int:
    """Calculate the next check interval using binary exponential backoff.

    Formula:
        interval = min(base_interval * 2^consecutive_failures, max_interval)

    On the first failure (consecutive_failures=1), the check interval doubles
    to satisfy US-16: 'A failing monitor should be checked less frequently'.
    When consecutive_failures <= 0, returns the base interval (bounded).
    """
    if consecutive_failures <= 0:
        return int(
            max(MIN_BACKOFF_INTERVAL_SECONDS, min(base_interval_seconds, max_interval_seconds))
        )

    exp = min(consecutive_failures, MAX_EXPONENT)
    backoff_interval = int(base_interval_seconds * (2**exp))
    return int(max(MIN_BACKOFF_INTERVAL_SECONDS, min(backoff_interval, max_interval_seconds)))


def apply_failure_backoff(
    monitor: Monitor,
    now: datetime | None = None,
    max_interval_seconds: int = MAX_BACKOFF_INTERVAL_SECONDS,
) -> int:
    """Update current_interval_seconds and backoff_until on a failing monitor.

    Uses monitor.check_interval_seconds as the base and monitor.consecutive_failures
    as the exponent. Calculates backoff_until in UTC.
    """
    base_interval = (
        monitor.check_interval_seconds
        if monitor.check_interval_seconds >= MIN_BACKOFF_INTERVAL_SECONDS
        else 60
    )
    new_interval = calculate_exponential_backoff(
        base_interval_seconds=base_interval,
        consecutive_failures=monitor.consecutive_failures,
        max_interval_seconds=max_interval_seconds,
    )

    current_time = now or datetime.now(UTC)
    monitor.current_interval_seconds = new_interval
    monitor.backoff_until = current_time + timedelta(seconds=new_interval)
    return new_interval


def reset_monitor_backoff(monitor: Monitor) -> None:
    """Reset a recovered monitor to its normal configured interval and clear backoff."""
    monitor.current_interval_seconds = monitor.check_interval_seconds
    monitor.backoff_until = None


def update_monitor_backoff(
    monitor: Monitor,
    is_healthy: bool,
    now: datetime | None = None,
) -> None:
    """Update backoff state based on health check outcome.

    - Healthy: resets current_interval_seconds and clears backoff_until.
    - Failing: escalates current_interval_seconds and sets backoff_until window.
    """
    if is_healthy:
        reset_monitor_backoff(monitor)
    else:
        apply_failure_backoff(monitor, now=now)

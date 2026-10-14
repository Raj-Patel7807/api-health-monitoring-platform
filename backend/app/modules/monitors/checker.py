"""Health check execution and failure classification (US-06).

Implements AC-06.1 through AC-06.6:
- AC-06.1: Expected status code is a success unless another condition fails.
- AC-06.2: Wrong status code is recorded as a failure.
- AC-06.3: Timeout is recorded as a timeout failure.
- AC-06.4: Connection failure is recorded as a connection failure.
- AC-06.5: SSL/TLS failure is recorded as an SSL failure.
- AC-06.6: A single failure increments consecutive_failures but does NOT open
           an incident by itself (incident logic belongs to a later story).
"""

import logging
import ssl
import time
from dataclasses import dataclass, field
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.modules.monitors.backoff import DEFAULT_USER_AGENT, update_monitor_backoff
from app.modules.monitors.models import Monitor

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Result data structure
# ---------------------------------------------------------------------------


@dataclass
class CheckResult:
    """Structured outcome of a single health check execution.

    Matches the columns of the health_check_results table (schema_mvp.sql).
    Storing and persisting this result is the responsibility of US-08 (Sprint 3).
    """

    monitor_id: str
    status: str  # "healthy" or "failing"
    http_status_code: int | None = None
    response_time_ms: int = 0
    timeout: bool = False
    connection_error: bool = False
    ssl_error: bool = False
    error_message: str | None = None
    # Counter snapshots after the check (useful for caller / US-09 incident logic)
    consecutive_failures: int = field(default=0, repr=False)
    consecutive_successes: int = field(default=0, repr=False)


# ---------------------------------------------------------------------------
# Core HTTP execution
# ---------------------------------------------------------------------------


def execute_http_check(
    url: str,
    method: str,
    expected_status_code: int,
    timeout_seconds: int,
    user_agent: str,
    monitor_id: str,
) -> CheckResult:
    """Perform one outbound HTTP request and classify the outcome.

    Uses a synchronous httpx.Client because Celery tasks are synchronous.
    Sends a custom User-Agent header as required by US-16 / DR2.
    Measures elapsed time with a monotonic clock for accuracy.

    Args:
        url: The endpoint URL to probe.
        method: HTTP method (GET, HEAD, POST, …).
        expected_status_code: The status code that means the endpoint is healthy.
        timeout_seconds: Maximum seconds to wait for a complete response.
        user_agent: Value for the User-Agent request header.
        monitor_id: String UUID of the monitor (used for logging and the result).

    Returns:
        A CheckResult describing the exact outcome.
    """
    result = CheckResult(monitor_id=monitor_id, status="healthy")
    headers = {"User-Agent": user_agent}

    start = time.perf_counter()
    try:
        with httpx.Client(timeout=timeout_seconds, verify=True) as client:
            response = client.request(method, url, headers=headers)

        elapsed_ms = int((time.perf_counter() - start) * 1000)
        result.response_time_ms = elapsed_ms
        result.http_status_code = response.status_code

        # AC-06.2 — wrong status code
        if response.status_code != expected_status_code:
            result.status = "failing"
            result.error_message = (
                f"Expected HTTP {expected_status_code}, got {response.status_code}"
            )
            logger.warning(
                "Monitor %s: wrong status code %s (expected %s)",
                monitor_id,
                response.status_code,
                expected_status_code,
            )

    # AC-06.3 — timeout
    except httpx.TimeoutException as exc:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        result.response_time_ms = elapsed_ms
        result.status = "failing"
        result.timeout = True
        result.error_message = f"Request timed out after {timeout_seconds}s: {exc}"
        logger.warning("Monitor %s: timeout after %ds", monitor_id, timeout_seconds)

    # AC-06.5 — SSL / TLS failure (must be checked before ConnectError because
    # httpx wraps SSL errors inside ConnectError on some platforms)
    except httpx.ConnectError as exc:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        result.response_time_ms = elapsed_ms
        result.status = "failing"

        cause = exc.__cause__
        if isinstance(cause, ssl.SSLError) or "SSL" in str(exc).upper():
            result.ssl_error = True
            result.error_message = f"SSL/TLS error: {exc}"
            logger.warning("Monitor %s: SSL/TLS failure — %s", monitor_id, exc)
        else:
            # AC-06.4 — connection failure (DNS, refused, unreachable …)
            result.connection_error = True
            result.error_message = f"Connection error: {exc}"
            logger.warning("Monitor %s: connection error — %s", monitor_id, exc)

    # AC-06.4 — other network-level or protocol errors (e.g. remote disconnect, reset)
    except (httpx.NetworkError, httpx.ProtocolError) as exc:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        result.response_time_ms = elapsed_ms
        result.status = "failing"
        result.connection_error = True
        result.error_message = f"Connection error: {exc}"
        logger.warning("Monitor %s: network/protocol error — %s", monitor_id, exc)

    return result


# ---------------------------------------------------------------------------
# Counter update (pure, no I/O — easy to unit-test)
# ---------------------------------------------------------------------------


def update_monitor_counters(monitor: Monitor, result: CheckResult) -> None:
    """Increment the appropriate counter and reset the opposite one.

    AC-06.6: a single failure increments consecutive_failures only.
    Incident creation from thresholds belongs to US-09, not here.
    """
    if result.status == "healthy":
        monitor.consecutive_successes += 1
        monitor.consecutive_failures = 0
    else:
        monitor.consecutive_failures += 1
        monitor.consecutive_successes = 0


# ---------------------------------------------------------------------------
# Orchestrator called by the Celery task
# ---------------------------------------------------------------------------


def check_monitor_by_id(
    monitor_id: str,
    db_session: Session | None = None,
) -> CheckResult | None:
    """Load a monitor, run its health check, update counters, and return the result.

    Args:
        monitor_id: String UUID of the monitor to check.
        db_session: Optional injected session (used in unit tests to avoid real DB).
                    When None, a real session is obtained via get_db_session().

    Returns:
        A CheckResult, or None if the monitor is not found / should be skipped.
    """

    def _run(session: Session) -> CheckResult | None:
        try:
            monitor_uuid = UUID(monitor_id)
        except ValueError:
            logger.error("Invalid monitor id %r — skipping check", monitor_id)
            return None

        monitor = session.get(Monitor, monitor_uuid)

        if monitor is None:
            logger.error("Monitor %s not found — skipping check", monitor_id)
            return None

        if monitor.deleted_at is not None:
            logger.info("Monitor %s is soft-deleted — skipping check", monitor_id)
            return None

        if not monitor.enabled:
            logger.info("Monitor %s is disabled — skipping check", monitor_id)
            return None

        user_agent = (
            monitor.user_agent.strip()
            if monitor.user_agent and monitor.user_agent.strip()
            else DEFAULT_USER_AGENT
        )
        result = execute_http_check(
            url=monitor.url,
            method=monitor.method,
            expected_status_code=monitor.expected_status_code,
            timeout_seconds=monitor.timeout_seconds,
            user_agent=user_agent,
            monitor_id=str(monitor.id),
        )

        update_monitor_counters(monitor, result)
        update_monitor_backoff(monitor, is_healthy=(result.status == "healthy"))
        result.consecutive_failures = monitor.consecutive_failures
        result.consecutive_successes = monitor.consecutive_successes

        session.add(monitor)
        session.commit()

        logger.info(
            "Monitor %s check complete: status=%s failures=%d successes=%d",
            monitor_id,
            result.status,
            monitor.consecutive_failures,
            monitor.consecutive_successes,
        )
        return result

    if db_session is not None:
        # Injected session — caller owns transaction lifecycle (used in tests)
        return _run(db_session)

    with get_db_session() as session:
        return _run(session)

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.results.models import HealthCheckResult

if TYPE_CHECKING:
    from app.modules.monitors.checker import CheckResult


BODY_EXCERPT_MAX_CHARS = 500


def _strip_nul(value: str | None) -> str | None:
    if value is None:
        return None

    return value.replace("\x00", "")


def build_result_row(
    result: CheckResult,
    monitor_id: UUID,
) -> HealthCheckResult:
    if result.status not in {"healthy", "failing"}:
        raise ValueError(f"Invalid health check status: {result.status}")

    transport_failure = result.timeout or result.connection_error or result.ssl_error

    if result.status == "healthy":
        excerpt = ""
    else:
        excerpt = _strip_nul((result.body_excerpt or "")[:BODY_EXCERPT_MAX_CHARS]) or ""

    return HealthCheckResult(
        monitor_id=monitor_id,
        checked_at=result.checked_at,
        status=result.status,
        http_status_code=(None if transport_failure else result.http_status_code),
        response_time_ms=(None if transport_failure else result.response_time_ms),
        timeout=result.timeout,
        connection_error=result.connection_error,
        ssl_error=result.ssl_error,
        error_message=_strip_nul(result.error_message),
        response_body_excerpt=excerpt,
    )


def record_check_result(
    session: Session,
    result: CheckResult,
    monitor_id: UUID,
) -> HealthCheckResult:
    row = build_result_row(result, monitor_id)
    session.add(row)
    return row

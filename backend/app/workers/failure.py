"""Celery worker failure recording and tracking.

Provides structured tracking of failed Celery worker tasks to meet AC-05.6:
The platform records or logs operational failures so that they can be investigated.
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

# Keys whose values must never be stored or logged in plain text
SENSITIVE_KEY_SUBSTRINGS = (
    "password",
    "token",
    "secret",
    "key",
    "authorization",
    "cookie",
    "webhook",
    "credential",
)


def sanitize_payload(value: Any) -> Any:
    """Sanitize arguments or metadata by redacting sensitive fields."""
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for k, v in value.items():
            k_lower = str(k).lower()
            if any(s in k_lower for s in SENSITIVE_KEY_SUBSTRINGS):
                sanitized[str(k)] = "[REDACTED]"
            else:
                sanitized[str(k)] = sanitize_payload(v)
        return sanitized
    if isinstance(value, (list, tuple)):
        return [sanitize_payload(v) for v in value]
    return value


@dataclass
class FailedTaskRecord:
    """Immutable-like record of a failed background worker task."""

    task_id: str
    task_name: str
    exception_type: str
    exception_message: str
    args: list[Any] = field(default_factory=list)
    kwargs: dict[str, Any] = field(default_factory=dict)
    traceback: str | None = None
    worker: str | None = None
    retries: int = 0
    failed_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Serialize failure record to a dictionary."""
        return {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "exception_type": self.exception_type,
            "exception_message": self.exception_message,
            "args": self.args,
            "kwargs": self.kwargs,
            "traceback": self.traceback,
            "worker": self.worker,
            "retries": self.retries,
            "failed_at": self.failed_at.isoformat(),
        }


class TaskFailureTracker:
    """Process-local, bounded diagnostic record of failed tasks.

    Records are not durable across worker restarts. Configure persistent
    operational log collection for investigating past task failures.
    """

    def __init__(self, max_entries: int = 200) -> None:
        self.max_entries = max_entries
        self._records: dict[str, FailedTaskRecord] = {}
        self._order: list[str] = []

    def record_failure(
        self,
        task_id: str,
        task_name: str,
        exception: BaseException,
        args: list[Any] | None = None,
        kwargs: dict[str, Any] | None = None,
        traceback: str | None = None,
        worker: str | None = None,
        retries: int = 0,
        now: datetime | None = None,
    ) -> FailedTaskRecord:
        """Record safe diagnostics without persisting untrusted exception text.

        Exception messages, tracebacks, and arbitrary task parameters can contain
        access tokens or credentials even when their keys look harmless. Preserve
        the exception type and task metadata while omitting those raw values.
        """
        record = FailedTaskRecord(
            task_id=task_id,
            task_name=task_name,
            exception_type=type(exception).__name__,
            exception_message="[REDACTED]",
            args=["[REDACTED]"] * len(args or []),
            kwargs={str(key): "[REDACTED]" for key in (kwargs or {})},
            traceback=None,
            worker=worker,
            retries=retries,
            failed_at=now or datetime.now(UTC),
        )

        if task_id in self._records:
            self._order.remove(task_id)
        elif len(self._order) >= self.max_entries:
            oldest_id = self._order.pop(0)
            self._records.pop(oldest_id, None)

        self._records[task_id] = record
        self._order.append(task_id)

        logger.error(
            "Recorded failed worker task %s[%s]: %s",
            task_name,
            task_id,
            record.exception_type,
            extra={
                "task_id": task_id,
                "task_name": task_name,
                "exception_type": record.exception_type,
                "retries": retries,
                "worker": worker,
            },
        )
        return record

    def get_failure(self, task_id: str) -> FailedTaskRecord | None:
        """Retrieve failure details by task ID."""
        return self._records.get(task_id)

    def list_failures(self, limit: int = 50) -> list[FailedTaskRecord]:
        """List recent failures in reverse chronological order."""
        recent_ids = list(reversed(self._order[-limit:]))
        return [self._records[tid] for tid in recent_ids if tid in self._records]

    def clear(self) -> None:
        """Clear recorded failures (primarily for test isolation)."""
        self._records.clear()
        self._order.clear()


_default_tracker = TaskFailureTracker()


def get_failure_tracker() -> TaskFailureTracker:
    """Return the global task failure tracker."""
    return _default_tracker


def record_failed_task(
    task_id: str,
    task_name: str,
    exception: BaseException,
    args: list[Any] | None = None,
    kwargs: dict[str, Any] | None = None,
    traceback: str | None = None,
    worker: str | None = None,
    retries: int = 0,
    now: datetime | None = None,
) -> FailedTaskRecord:
    """Convenience helper to record a failed task in the default tracker."""
    return _default_tracker.record_failure(
        task_id=task_id,
        task_name=task_name,
        exception=exception,
        args=args,
        kwargs=kwargs,
        traceback=traceback,
        worker=worker,
        retries=retries,
        now=now,
    )


def get_failed_task(task_id: str) -> FailedTaskRecord | None:
    """Convenience helper to retrieve a failed task record."""
    return _default_tracker.get_failure(task_id)


def list_failed_tasks(limit: int = 50) -> list[FailedTaskRecord]:
    """Convenience helper to list recent failed task records."""
    return _default_tracker.list_failures(limit=limit)

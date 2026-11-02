"""Celery signal handlers for task lifecycle, failure recording, and retry logging."""

from __future__ import annotations

import logging
from typing import Any

from app.workers.failure import record_failed_task

try:
    from celery.signals import task_failure, task_retry  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover

    class _Signal:
        def connect(self, func: Any) -> Any:
            return func

    task_failure = _Signal()  # type: ignore[assignment]
    task_retry = _Signal()  # type: ignore[assignment]

logger = logging.getLogger(__name__)


@task_failure.connect  # type: ignore[misc]
def handle_task_failure(
    sender: Any = None,
    task_id: str | None = None,
    exception: BaseException | None = None,
    args: tuple[Any, ...] | None = None,
    kwargs: dict[str, Any] | None = None,
    traceback: Any = None,
    einfo: Any = None,
    **extra: Any,
) -> None:
    """Record and log task failures when any Celery task fails."""
    if not task_id or exception is None:
        return

    task_name = getattr(sender, "name", str(sender)) if sender else "unknown_task"
    retries = getattr(sender.request, "retries", 0) if hasattr(sender, "request") else 0
    worker = getattr(sender.request, "hostname", None) if hasattr(sender, "request") else None

    record_failed_task(
        task_id=task_id,
        task_name=task_name,
        exception=exception,
        args=list(args) if args else [],
        kwargs=kwargs or {},
        worker=worker,
        retries=retries,
    )


@task_retry.connect  # type: ignore[misc]
def handle_task_retry(
    sender: Any = None,
    task_id: str | None = None,
    reason: BaseException | None = None,
    einfo: Any = None,
    **extra: Any,
) -> None:
    """Log structured warnings whenever a task execution is scheduled for retry."""
    task_name = getattr(sender, "name", str(sender)) if sender else "unknown_task"
    retries = getattr(sender.request, "retries", 0) if hasattr(sender, "request") else 0
    max_retries = getattr(sender, "max_retries", None)

    logger.warning(
        "Celery task retrying: %s[%s] attempt=%s max_retries=%s reason_type=%s",
        task_name,
        task_id,
        retries,
        max_retries,
        type(reason).__name__ if reason else None,
        extra={
            "task_id": task_id,
            "task_name": task_name,
            "retries": retries,
            "max_retries": max_retries,
            "exception_type": type(reason).__name__ if reason else None,
        },
    )

import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.modules.monitors.models import Monitor
from app.workers.celery_app import SCHEDULER_POLL_SECONDS, celery_app

logger = logging.getLogger(__name__)


def find_and_schedule_due_monitors(
    session: Session,
    now: datetime | None = None,
    task_dispatcher: Callable[[str, str], object] | None = None,
) -> list[str]:
    """Find monitors due for health checks, advance next_check_at, and queue check tasks.

    Respects soft deletion, enabled status, and backoff_until windows.
    Updates next_check_at using current_interval_seconds in UTC.
    """
    current_time = now or datetime.now(UTC)
    dispatcher = task_dispatcher or (
        lambda m_id, check_id: celery_app.send_task(
            "app.workers.tasks.run_health_check", args=[m_id, check_id], queue="monitoring"
        )
    )

    try:
        due = (
            Monitor.enabled.is_(True),
            Monitor.deleted_at.is_(None),
            or_(
                Monitor.next_check_at.is_(None),
                Monitor.next_check_at <= current_time,
            ),
            or_(
                Monitor.backoff_until.is_(None),
                Monitor.backoff_until <= current_time,
            ),
        )
        due_ids = list(session.scalars(select(Monitor.id).where(*due)))
        queued_ids: list[str] = []

        for monitor_id in due_ids:
            monitor = session.scalar(
                select(Monitor)
                .where(Monitor.id == monitor_id, *due)
                .with_for_update(skip_locked=True)
                .execution_options(populate_existing=True)
            )
            if monitor is None:
                continue
            interval = (
                monitor.current_interval_seconds
                if monitor.current_interval_seconds > 0
                else monitor.check_interval_seconds
            )
            if interval <= 0:
                interval = 60

            # Keep the planned cadence when this poll is slightly late. After a
            # missed poll or a backoff, start from now to avoid catch-up probes.
            scheduled_for = monitor.next_check_at or current_time
            late_by = current_time - scheduled_for
            if monitor.backoff_until is not None or late_by >= timedelta(
                seconds=min(interval, SCHEDULER_POLL_SECONDS)
            ):
                scheduled_for = current_time
            monitor.next_check_at = scheduled_for + timedelta(seconds=interval)
            monitor_id_str = str(monitor.id)
            # A lost or delayed message is re-published with the same identifier.
            monitor.pending_check_id = monitor.pending_check_id or uuid4()
            dispatcher(monitor_id_str, str(monitor.pending_check_id))
            session.commit()
            queued_ids.append(monitor_id_str)

        session.commit()
        if queued_ids:
            logger.info(
                "Scheduled %d due monitors for background health checks",
                len(queued_ids),
                extra={"queued_count": len(queued_ids)},
            )
        return queued_ids
    except Exception:
        session.rollback()
        logger.exception("Failed to schedule due monitors")
        raise

import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.modules.monitors.models import Monitor
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def find_and_schedule_due_monitors(
    session: Session,
    now: datetime | None = None,
    task_dispatcher: Callable[[str], object] | None = None,
) -> list[str]:
    """Find monitors due for health checks, advance next_check_at, and queue check tasks.

    Respects soft deletion, enabled status, and backoff_until windows.
    Updates next_check_at using current_interval_seconds in UTC.
    """
    current_time = now or datetime.now(UTC)
    dispatcher = task_dispatcher or (
        lambda m_id: celery_app.send_task(
            "app.workers.tasks.run_health_check", args=[m_id], queue="monitoring"
        )
    )

    try:
        stmt = select(Monitor).where(
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
        due_monitors = list(session.scalars(stmt).all())
        queued_ids: list[str] = []

        for monitor in due_monitors:
            interval = (
                monitor.current_interval_seconds
                if monitor.current_interval_seconds > 0
                else monitor.check_interval_seconds
            )
            if interval <= 0:
                interval = 60

            monitor.next_check_at = current_time + timedelta(seconds=interval)
            monitor_id_str = str(monitor.id)
            dispatcher(monitor_id_str)
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

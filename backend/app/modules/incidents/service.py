"""Incident service layer for threshold-based incident transitions (US-09)

and state machine recovery / read APIs (US-10 / Task B4).

State derivation rule:
---------------------
No dedicated column is added for the derived state.
State is computed dynamically based on the monitor's counters and active incident:
1. When status is 'resolved':
   The incident state is 'resolved' (endpoint is recovered and healthy).
2. When status is 'open':
   - If recovery_count > 0 (or monitor.consecutive_successes > 0):
     State is 'recovering'.
   - Else:
     State is 'failing'.
"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import event, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.modules.incidents.hooks import schedule_incident_resolved_hook
from app.modules.incidents.models import (
    Incident,
    IncidentStatus,
    get_incident_opened_hooks,
)
from app.modules.incidents.schemas import (
    IncidentDetailResponse,
    IncidentResponse,
)
from app.modules.monitors.backoff import reset_monitor_backoff
from app.modules.monitors.models import Monitor

logger = logging.getLogger(__name__)


def derive_incident_state(incident: Incident, monitor: Monitor | None = None) -> str:
    """Derive incident state dynamically without requiring a separate database column.

    Rule:
    - If status == 'resolved': state is 'resolved'
    - If status == 'open':
        - If incident.recovery_count > 0 or (monitor and monitor.consecutive_successes > 0):
          state is 'recovering'
        - Else: state is 'failing'
    """
    if str(incident.status).lower() == IncidentStatus.RESOLVED.value:
        return "resolved"
    if incident.recovery_count > 0 or (monitor is not None and monitor.consecutive_successes > 0):
        return "recovering"
    return "failing"


def process_monitor_failure(
    session: Session,
    monitor: Monitor,
    consecutive_failures: int,
) -> Incident | None:
    """Evaluate consecutive failures against the monitor's threshold (US-09).

    Args:
        session: Active database session.
        monitor: The Monitor instance.
        consecutive_failures: The current number of consecutive failures (atomic snapshot).

    Returns:
        The open Incident if threshold reached/exceeded, else None.
    """
    if consecutive_failures < monitor.failure_threshold:
        return None

    # Check if an open incident already exists for this monitor
    existing_incident = session.execute(
        select(Incident).where(
            Incident.monitor_id == monitor.id,
            Incident.status == "open",
        )
    ).scalar_one_or_none()

    if existing_incident is not None:
        # Atomic increment of existing open incident's failure_count
        # and reset recovery progress if failure occurred mid-recovery (US-10)
        if existing_incident.recovery_count > 0:
            existing_incident.recovery_count = 0
            row = session.execute(
                update(Incident)
                .where(Incident.id == existing_incident.id)
                .values(
                    failure_count=Incident.failure_count + 1,
                    recovery_count=0,
                )
                .returning(Incident.failure_count)
            ).one()
        else:
            row = session.execute(
                update(Incident)
                .where(Incident.id == existing_incident.id)
                .values(failure_count=Incident.failure_count + 1)
                .returning(Incident.failure_count)
            ).one()
        existing_incident.failure_count = row[0]
        return existing_incident

    # No open incident found; attempt to create a new one.
    now = datetime.now(UTC)
    incident = Incident(
        monitor_id=monitor.id,
        status="open",
        opened_at=now,
        failure_count=consecutive_failures,
        recovery_count=0,
    )

    try:
        # Use a nested transaction (savepoint) so that a concurrent insert conflict
        # does not invalidate the outer session/transaction.
        with session.begin_nested():
            session.add(incident)
            session.flush()

        # If flush succeeded, this is a newly opened incident.
        # Schedule post-commit hooks to fire after the transaction successfully commits.
        _schedule_incident_opened_hooks(session, incident)
        return incident

    except IntegrityError:
        # Another concurrent worker created an open incident at the same moment.
        # The savepoint automatically rolled back, keeping session clean.
        logger.info(
            "Concurrent incident conflict for monitor %s; fetching existing open incident.",
            monitor.id,
        )
        # Fetch the winner's open incident and increment failure_count
        conflicted_incident = session.execute(
            select(Incident).where(
                Incident.monitor_id == monitor.id,
                Incident.status == "open",
            )
        ).scalar_one_or_none()

        if conflicted_incident is not None:
            if conflicted_incident.recovery_count > 0:
                conflicted_incident.recovery_count = 0
                row = session.execute(
                    update(Incident)
                    .where(Incident.id == conflicted_incident.id)
                    .values(
                        failure_count=Incident.failure_count + 1,
                        recovery_count=0,
                    )
                    .returning(Incident.failure_count)
                ).one()
            else:
                row = session.execute(
                    update(Incident)
                    .where(Incident.id == conflicted_incident.id)
                    .values(failure_count=Incident.failure_count + 1)
                    .returning(Incident.failure_count)
                ).one()
            conflicted_incident.failure_count = row[0]
            return conflicted_incident

        # Edge case: if the conflicting incident was somehow resolved instantly
        return None


def _schedule_incident_opened_hooks(session: Session, incident: Incident) -> None:
    """Attach an after_commit listener on the session to invoke registered hooks."""
    incident_id = incident.id
    monitor_id = incident.monitor_id
    failure_count = incident.failure_count
    opened_at = incident.opened_at

    def _on_commit(_session: Session) -> None:
        hooks = get_incident_opened_hooks()
        for hook in hooks:
            try:
                hook(incident_id, monitor_id, failure_count, opened_at)
            except Exception:
                logger.exception("Error executing incident-opened hook %r", hook)

    # Use once=True so this listener executes only for this transaction's commit
    event.listen(session, "after_commit", _on_commit, once=True)


def process_incident_state_transition(
    session: Session,
    monitor: Monitor,
    is_healthy: bool,
) -> Incident | None:
    """Execute the incident state machine transition for a given monitor health check outcome.

    Transitions:
    - Healthy check with open incident:
      Counts recovery progress. When recovery_threshold is met, resolves incident,
      clears monitor failure & success counters, resets backoff, and queues post-commit hook.
    - Failing check with open incident:
      Increments failure_count. If recovery progress was in-flight, resets recovery progress.
    - Failing check without open incident:
      Delegates to process_monitor_failure to open a new incident once failure_threshold is reached.
    """
    now = datetime.now(UTC)
    recovery_threshold = max(1, monitor.recovery_threshold)

    # Check if an open incident already exists for this monitor
    open_incident = session.execute(
        select(Incident).where(
            Incident.monitor_id == monitor.id,
            Incident.status == "open",
        )
    ).scalar_one_or_none()

    if is_healthy:
        if open_incident is None:
            return None

        # AC: With an open incident, count consecutive successes
        open_incident.recovery_count += 1

        if open_incident.recovery_count >= recovery_threshold:
            # AC: At recovery_threshold, resolve incident and reset monitor's counters
            open_incident.status = "resolved"
            open_incident.resolved_at = now

            # Reset monitor counters
            monitor.consecutive_failures = 0
            monitor.consecutive_successes = 0

            # Reset backoff fields and schedule normal frequency (US-16)
            reset_monitor_backoff(monitor, now=now)

            # Schedule post-commit hook for B5
            schedule_incident_resolved_hook(session, open_incident.id)

            logger.info(
                "Incident %s resolved for monitor %s (recovery_threshold=%d reached)",
                open_incident.id,
                monitor.id,
                recovery_threshold,
            )
        else:
            logger.info(
                "Incident %s in recovery for monitor %s: %d/%d consecutive successes",
                open_incident.id,
                monitor.id,
                open_incident.recovery_count,
                recovery_threshold,
            )
        return open_incident

    # Check failed:
    if open_incident is not None:
        open_incident.failure_count += 1
        # AC: A failure during recovery resets recovery progress; the incident stays open.
        if open_incident.recovery_count > 0:
            logger.warning(
                "Incident %s recovery reset to 0 for monitor %s due to failure",
                open_incident.id,
                monitor.id,
            )
            open_incident.recovery_count = 0
            monitor.consecutive_successes = 0
        return open_incident

    # No open incident exists — check failure threshold to open one (US-09)
    return process_monitor_failure(session, monitor, monitor.consecutive_failures)


async def list_incidents(
    db: AsyncSession,
    team_id: UUID,
    status_filter: IncidentStatus | None = None,
    monitor_id: UUID | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[IncidentResponse], int]:
    """List paginated incidents belonging to monitors owned by *team_id*."""
    safe_page = max(1, page)
    safe_page_size = max(1, min(100, page_size))

    base_filter = [
        Monitor.team_id == team_id,
        Monitor.deleted_at.is_(None),
    ]

    if monitor_id is not None:
        base_filter.append(Incident.monitor_id == monitor_id)

    if status_filter is not None:
        base_filter.append(Incident.status == status_filter.value)

    # Count total matching incidents
    count_stmt = (
        select(func.count(Incident.id))
        .join(Monitor, Incident.monitor_id == Monitor.id)
        .where(*base_filter)
    )
    count_res = await db.execute(count_stmt)
    total = count_res.scalar_one() or 0

    # Paginated query, newest first
    offset = (safe_page - 1) * safe_page_size
    query_stmt = (
        select(Incident, Monitor)
        .join(Monitor, Incident.monitor_id == Monitor.id)
        .where(*base_filter)
        .order_by(Incident.opened_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(query_stmt)
    rows = result.all()

    items = [
        IncidentResponse(
            id=inc.id,
            monitor_id=inc.monitor_id,
            status=IncidentStatus(inc.status),
            opened_at=inc.opened_at,
            resolved_at=inc.resolved_at,
            failure_count=inc.failure_count,
            recovery_count=inc.recovery_count,
            state=derive_incident_state(inc, mon),
        )
        for inc, mon in rows
    ]

    return items, total


async def get_incident(
    db: AsyncSession,
    team_id: UUID,
    incident_id: UUID,
) -> IncidentDetailResponse | None:
    """Retrieve an incident with monitor_url, scoped strictly to *team_id*."""
    stmt = (
        select(Incident, Monitor)
        .join(Monitor, Incident.monitor_id == Monitor.id)
        .where(
            Incident.id == incident_id,
            Monitor.team_id == team_id,
            Monitor.deleted_at.is_(None),
        )
    )
    result = await db.execute(stmt)
    row = result.first()
    if row is None:
        return None

    incident, monitor = row
    return IncidentDetailResponse(
        id=incident.id,
        monitor_id=incident.monitor_id,
        monitor_url=monitor.url,
        status=IncidentStatus(incident.status),
        opened_at=incident.opened_at,
        resolved_at=incident.resolved_at,
        failure_count=incident.failure_count,
        recovery_count=incident.recovery_count,
        state=derive_incident_state(incident, monitor),
    )

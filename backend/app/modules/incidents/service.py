"""Incident service layer for threshold-based incident transitions (US-09).

Implements:
- Incident opening when consecutive_failures >= failure_threshold and no open incident exists.
- Atomic incident failure_count incrementing when an incident is already open.
- Safe concurrency handling for simultaneous check results via unique index collision recovery.
- Post-commit hook notification firing exactly once per newly opened incident.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import event, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.incidents.models import Incident, get_incident_opened_hooks
from app.modules.monitors.models import Monitor

logger = logging.getLogger(__name__)


def process_monitor_failure(
    session: Session,
    monitor: Monitor,
    consecutive_failures: int,
) -> Incident | None:
    """Evaluate consecutive failures against the monitor's threshold and manage incident state.

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

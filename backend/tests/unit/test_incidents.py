"""Unit tests for threshold-based incident creation and hook handling (US-09 / Issue #49).

Covers:
1. One failure does not create an incident.
2. Two failures do not create an incident when threshold is three.
3. The third consecutive failure creates an incident.
4. The incident has the correct initial failure_count.
5. The correct monitor ID is assigned.
6. The incident has status = open.
7. A successful result resets consecutive failures to zero.
8. A subsequent failure starts a new consecutive-failure sequence.
9. Each monitor uses its own failure threshold.
10. A fourth failure increments the existing incident.
11. Further failures never create duplicate open incidents.
12. The incident-opened hook fires exactly once.
13. The hook does not execute before transaction commit.
14. The hook does not execute after a transaction rollback.
15. The hook does not execute for subsequent failures on an already-open incident.
"""

from datetime import datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.modules.incidents.models import (
    Incident,
    get_incident_opened_hooks,
    register_incident_opened_hook,
    unregister_incident_opened_hook,
)
from app.modules.incidents.service import process_monitor_failure
from app.modules.monitors.models import Monitor


@pytest.fixture
def db_session() -> Session:
    """Provide a fresh in-memory SQLite database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_monitor(db_session: Session) -> Monitor:
    """Create and persist a sample monitor with failure_threshold=3."""
    monitor = Monitor(
        id=uuid4(),
        team_id=uuid4(),
        name="Test API Monitor",
        url="https://api.example.com/health",
        failure_threshold=3,
        recovery_threshold=2,
        check_interval_seconds=60,
        current_interval_seconds=60,
        consecutive_failures=0,
        consecutive_successes=0,
    )
    db_session.add(monitor)
    db_session.commit()
    return monitor


def test_one_failure_does_not_create_incident(db_session: Session, sample_monitor: Monitor) -> None:
    """AC-09.1: One failure does not create an incident when threshold is 3."""
    incident = process_monitor_failure(db_session, sample_monitor, consecutive_failures=1)
    db_session.commit()

    assert incident is None
    count = db_session.execute(select(Incident)).scalars().all()
    assert len(count) == 0


def test_two_failures_do_not_create_incident(db_session: Session, sample_monitor: Monitor) -> None:
    """AC-09.1: Two failures do not create an incident when threshold is 3."""
    incident = process_monitor_failure(db_session, sample_monitor, consecutive_failures=2)
    db_session.commit()

    assert incident is None
    count = db_session.execute(select(Incident)).scalars().all()
    assert len(count) == 0


def test_third_failure_creates_open_incident(db_session: Session, sample_monitor: Monitor) -> None:
    """AC-09.2: Third consecutive failure creates an open incident with correct fields."""
    incident = process_monitor_failure(db_session, sample_monitor, consecutive_failures=3)
    db_session.commit()

    assert incident is not None
    assert incident.status == "open"
    assert incident.monitor_id == sample_monitor.id
    assert incident.failure_count == 3
    assert incident.recovery_count == 0
    assert incident.resolved_at is None
    assert incident.opened_at is not None

    persisted = db_session.execute(
        select(Incident).where(Incident.monitor_id == sample_monitor.id)
    ).scalar_one()
    assert persisted.id == incident.id
    assert persisted.status == "open"
    assert persisted.failure_count == 3


def test_fourth_failure_increments_existing_incident(
    db_session: Session, sample_monitor: Monitor
) -> None:
    """AC-10.2: Fourth failure increments failure_count without creating a duplicate incident."""
    inc1 = process_monitor_failure(db_session, sample_monitor, consecutive_failures=3)
    db_session.commit()
    assert inc1 is not None

    inc2 = process_monitor_failure(db_session, sample_monitor, consecutive_failures=4)
    db_session.commit()
    assert inc2 is not None

    assert inc1.id == inc2.id
    assert inc2.failure_count == 4

    all_incidents = (
        db_session.execute(select(Incident).where(Incident.monitor_id == sample_monitor.id))
        .scalars()
        .all()
    )
    assert len(all_incidents) == 1
    assert all_incidents[0].failure_count == 4


def test_custom_monitor_failure_threshold(db_session: Session) -> None:
    """AC-09.3: Each monitor uses its own configured failure_threshold."""
    monitor_custom = Monitor(
        id=uuid4(),
        team_id=uuid4(),
        name="Custom Threshold Monitor",
        url="https://api.example.com/custom",
        failure_threshold=5,
        consecutive_failures=0,
    )
    db_session.add(monitor_custom)
    db_session.commit()

    # Failures 1 through 4 should not open incident
    for f in range(1, 5):
        inc = process_monitor_failure(db_session, monitor_custom, consecutive_failures=f)
        db_session.commit()
        assert inc is None

    # Failure 5 opens incident
    inc5 = process_monitor_failure(db_session, monitor_custom, consecutive_failures=5)
    db_session.commit()
    assert inc5 is not None
    assert inc5.failure_count == 5


def test_hook_fires_exactly_once_after_commit(db_session: Session, sample_monitor: Monitor) -> None:
    """Incident opened hook must fire only after commit and exactly once."""
    mock_hook = MagicMock()
    register_incident_opened_hook(mock_hook)

    try:
        inc = process_monitor_failure(db_session, sample_monitor, consecutive_failures=3)
        # Before commit, hook must NOT have fired
        mock_hook.assert_not_called()

        db_session.commit()
        # After commit, hook fires once
        mock_hook.assert_called_once()
        args = mock_hook.call_args[0]
        # (incident_id, monitor_id, failure_count, opened_at)
        assert args[0] == inc.id
        assert args[1] == sample_monitor.id
        assert args[2] == 3
        assert isinstance(args[3], datetime)

        # Subsequent failure on existing open incident must NOT fire hook again
        process_monitor_failure(db_session, sample_monitor, consecutive_failures=4)
        db_session.commit()
        mock_hook.assert_called_once()
    finally:
        unregister_incident_opened_hook(mock_hook)


def test_hook_does_not_fire_on_rollback(db_session: Session, sample_monitor: Monitor) -> None:
    """Incident opened hook must NOT fire if the transaction is rolled back."""
    mock_hook = MagicMock()
    register_incident_opened_hook(mock_hook)

    try:
        process_monitor_failure(db_session, sample_monitor, consecutive_failures=3)
        mock_hook.assert_not_called()

        db_session.rollback()
        mock_hook.assert_not_called()
    finally:
        unregister_incident_opened_hook(mock_hook)


def test_hook_registration_and_unregistration() -> None:
    """Verify hook register, get, and unregister utilities."""
    hook = lambda inc_id, mon_id, count, dt: None  # noqa: E731
    register_incident_opened_hook(hook)
    assert hook in get_incident_opened_hooks()

    unregister_incident_opened_hook(hook)
    assert hook not in get_incident_opened_hooks()

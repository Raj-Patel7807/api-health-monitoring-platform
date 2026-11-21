"""Unit tests for the incident state machine and post-commit hooks (US-10 / Task B4).

Tests cover:
- State transitions: Healthy -> Failing -> Recovering -> Healthy
- Counting consecutive successes during recovery
- Resolving on recovery_threshold (status=resolved, resolved_at set)
- Resetting monitor counters (failures=0, successes=0) and backoff fields
- Resetting recovery progress on failure during recovery while incident remains open
- Opening a brand new incident row after previous incident resolution
- Post-commit hook firing strictly once per incident only after database commit
"""

from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.modules.incidents.hooks import (
    clear_incident_resolved_hooks,
    register_incident_resolved_hook,
)
from app.modules.incidents.models import Incident, IncidentStatus
from app.modules.incidents.service import (
    derive_incident_state,
    process_incident_state_transition,
)
from app.modules.monitors.models import Monitor


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    """Isolated in-memory SQLite session for state machine tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()


@pytest.fixture(autouse=True)
def _cleanup_hooks() -> Generator[None, None, None]:
    clear_incident_resolved_hooks()
    yield
    clear_incident_resolved_hooks()


def _create_test_monitor(
    session: Session,
    failure_threshold: int = 3,
    recovery_threshold: int = 2,
    check_interval_seconds: int = 60,
) -> Monitor:
    monitor = Monitor(
        id=uuid4(),
        team_id=uuid4(),
        name="Test API Monitor",
        url="https://api.example.com/health",
        method="GET",
        enabled=True,
        check_interval_seconds=check_interval_seconds,
        current_interval_seconds=check_interval_seconds,
        timeout_seconds=10,
        expected_status_code=200,
        failure_threshold=failure_threshold,
        recovery_threshold=recovery_threshold,
        consecutive_failures=0,
        consecutive_successes=0,
    )
    session.add(monitor)
    session.commit()
    return monitor


def test_recovery_threshold_requires_exact_consecutive_successes(db_session: Session) -> None:
    """AC-10.3: With recovery_threshold 2, one success does not resolve; two in a row do."""
    monitor = _create_test_monitor(db_session, recovery_threshold=2)

    # Initial open incident
    incident = Incident(
        id=uuid4(),
        monitor_id=monitor.id,
        status=IncidentStatus.OPEN,
        opened_at=datetime.now(UTC),
        failure_count=3,
        recovery_count=0,
    )
    db_session.add(incident)
    db_session.commit()

    assert derive_incident_state(incident, monitor) == "failing"

    # First healthy check: counts 1 success, remains open in recovering state
    res1 = process_incident_state_transition(db_session, monitor, is_healthy=True)
    assert res1 is not None
    assert res1.id == incident.id
    assert res1.status == IncidentStatus.OPEN
    assert res1.recovery_count == 1
    assert res1.resolved_at is None
    assert derive_incident_state(res1, monitor) == "recovering"

    # Second healthy check: reaches recovery_threshold=2 -> resolves incident
    res2 = process_incident_state_transition(db_session, monitor, is_healthy=True)
    assert res2 is not None
    assert res2.id == incident.id
    assert res2.status == IncidentStatus.RESOLVED
    assert res2.resolved_at is not None
    assert res2.recovery_count == 2
    assert derive_incident_state(res2, monitor) == "resolved"

    # Monitor counters must be reset
    assert monitor.consecutive_failures == 0
    assert monitor.consecutive_successes == 0


def test_failure_during_recovery_resets_progress(db_session: Session) -> None:
    """AC: A failure after one success resets recovery progress; the incident stays open."""
    monitor = _create_test_monitor(db_session, recovery_threshold=2)

    incident = Incident(
        id=uuid4(),
        monitor_id=monitor.id,
        status=IncidentStatus.OPEN,
        opened_at=datetime.now(UTC),
        failure_count=3,
        recovery_count=0,
    )
    db_session.add(incident)
    db_session.commit()

    # Progress: 1 success
    process_incident_state_transition(db_session, monitor, is_healthy=True)
    assert incident.recovery_count == 1
    assert incident.status == IncidentStatus.OPEN
    assert derive_incident_state(incident, monitor) == "recovering"

    # Failure occurs before reaching recovery_threshold
    res = process_incident_state_transition(db_session, monitor, is_healthy=False)
    assert res is not None
    assert res.id == incident.id
    assert res.status == IncidentStatus.OPEN
    assert res.recovery_count == 0  # Reset back to 0
    assert res.failure_count == 4  # Incremented
    assert derive_incident_state(res, monitor) == "failing"


def test_resolving_resets_backoff_and_counters(db_session: Session) -> None:
    """AC: Resolving clears monitor's failure/success counters and backoff fields."""
    monitor = _create_test_monitor(db_session, recovery_threshold=1, check_interval_seconds=60)
    monitor.consecutive_failures = 4
    monitor.consecutive_successes = 0
    monitor.current_interval_seconds = 480  # Backed off
    monitor.backoff_until = datetime.now(UTC)
    db_session.commit()

    incident = Incident(
        id=uuid4(),
        monitor_id=monitor.id,
        status=IncidentStatus.OPEN,
        opened_at=datetime.now(UTC),
        failure_count=4,
        recovery_count=0,
    )
    db_session.add(incident)
    db_session.commit()

    # 1 success meets recovery_threshold=1
    resolved = process_incident_state_transition(db_session, monitor, is_healthy=True)
    assert resolved is not None
    assert resolved.status == IncidentStatus.RESOLVED

    assert monitor.consecutive_failures == 0
    assert monitor.consecutive_successes == 0
    assert monitor.current_interval_seconds == 60
    assert monitor.backoff_until is None


def test_new_failure_streak_after_resolution_opens_new_incident_row(
    db_session: Session,
) -> None:
    """AC: A new failure streak after resolution opens a new incident (a new row)."""
    monitor = _create_test_monitor(db_session, failure_threshold=3, recovery_threshold=1)

    # Initial incident that gets resolved
    incident_1 = Incident(
        id=uuid4(),
        monitor_id=monitor.id,
        status=IncidentStatus.OPEN,
        opened_at=datetime.now(UTC),
        failure_count=3,
        recovery_count=0,
    )
    db_session.add(incident_1)
    db_session.commit()

    # Resolve incident 1
    process_incident_state_transition(db_session, monitor, is_healthy=True)
    assert incident_1.status == IncidentStatus.RESOLVED

    # Now monitor undergoes new failures
    monitor.consecutive_failures = 1
    res1 = process_incident_state_transition(db_session, monitor, is_healthy=False)
    assert res1 is None  # Below failure_threshold=3

    monitor.consecutive_failures = 2
    res2 = process_incident_state_transition(db_session, monitor, is_healthy=False)
    assert res2 is None

    # Hits failure_threshold=3
    monitor.consecutive_failures = 3
    res3 = process_incident_state_transition(db_session, monitor, is_healthy=False)
    assert res3 is not None
    assert res3.id != incident_1.id  # Brand new row
    assert res3.status == IncidentStatus.OPEN
    assert res3.failure_count == 3
    assert res3.recovery_count == 0


def test_resolved_hook_fires_once_only_after_commit(db_session: Session) -> None:
    """AC: The 'resolved' hook fires once per incident, only after commit."""
    mock_hook = MagicMock()
    register_incident_resolved_hook(mock_hook)

    monitor = _create_test_monitor(db_session, recovery_threshold=1)
    incident = Incident(
        id=uuid4(),
        monitor_id=monitor.id,
        status=IncidentStatus.OPEN,
        opened_at=datetime.now(UTC),
        failure_count=3,
        recovery_count=0,
    )
    db_session.add(incident)
    db_session.commit()

    # Trigger resolution
    resolved = process_incident_state_transition(db_session, monitor, is_healthy=True)
    assert resolved is not None
    assert resolved.status == IncidentStatus.RESOLVED

    # Prior to commit, hook MUST NOT fire
    mock_hook.assert_not_called()

    # Once committed, hook fires
    db_session.commit()
    mock_hook.assert_called_once_with(incident.id)

    # Calling commit again MUST NOT re-fire the hook
    db_session.commit()
    assert mock_hook.call_count == 1


def test_resolved_hook_never_fires_on_rollback(db_session: Session) -> None:
    """Hook must not fire if the transaction is rolled back."""
    mock_hook = MagicMock()
    register_incident_resolved_hook(mock_hook)

    monitor = _create_test_monitor(db_session, recovery_threshold=1)
    incident = Incident(
        id=uuid4(),
        monitor_id=monitor.id,
        status=IncidentStatus.OPEN,
        opened_at=datetime.now(UTC),
        failure_count=3,
        recovery_count=0,
    )
    db_session.add(incident)
    db_session.commit()

    # Trigger resolution which schedules the hook within an active transaction
    resolved = process_incident_state_transition(db_session, monitor, is_healthy=True)
    assert resolved is not None
    assert resolved.status == IncidentStatus.RESOLVED

    # Rollback instead of commit
    db_session.rollback()
    mock_hook.assert_not_called()

    # Subsequent commit should also not fire it
    db_session.commit()
    mock_hook.assert_not_called()


def test_derive_incident_state_rules() -> None:
    """Verify state derivation matches documented rules."""
    monitor = Monitor(consecutive_failures=0, consecutive_successes=0)

    # Resolved incident
    resolved_inc = Incident(
        status=IncidentStatus.RESOLVED,
        recovery_count=2,
    )
    assert derive_incident_state(resolved_inc, monitor) == "resolved"

    # Open incident with recovery progress
    recovering_inc = Incident(
        status=IncidentStatus.OPEN,
        recovery_count=1,
    )
    assert derive_incident_state(recovering_inc, monitor) == "recovering"

    # Open incident without recovery progress
    failing_inc = Incident(
        status=IncidentStatus.OPEN,
        recovery_count=0,
    )
    assert derive_incident_state(failing_inc, monitor) == "failing"


def test_hook_exception_does_not_break_transaction_or_subsequent_hooks(
    db_session: Session,
) -> None:
    """A failing B5 alert hook must not crash the transaction or prevent other hooks."""
    failing_hook = MagicMock(side_effect=RuntimeError("Slack alert delivery connection failed"))
    successful_hook = MagicMock()

    register_incident_resolved_hook(failing_hook)
    register_incident_resolved_hook(successful_hook)

    monitor = _create_test_monitor(db_session, recovery_threshold=1)
    incident = Incident(
        id=uuid4(),
        monitor_id=monitor.id,
        status=IncidentStatus.OPEN,
        opened_at=datetime.now(UTC),
        failure_count=3,
        recovery_count=0,
    )
    db_session.add(incident)
    db_session.commit()

    # Trigger resolution
    resolved = process_incident_state_transition(db_session, monitor, is_healthy=True)
    assert resolved is not None
    assert resolved.status == IncidentStatus.RESOLVED

    # Commit transaction — must not raise exception despite failing_hook
    db_session.commit()

    # Both hooks were invoked
    failing_hook.assert_called_once_with(incident.id)
    successful_hook.assert_called_once_with(incident.id)


def test_recovery_threshold_three_progression_and_reset(db_session: Session) -> None:
    """Test full cycle with higher recovery threshold (3):

    1 success -> 2 successes -> failure (resets to 0) -> 1 -> 2 -> 3 (resolves).
    """
    monitor = _create_test_monitor(db_session, recovery_threshold=3)
    incident = Incident(
        id=uuid4(),
        monitor_id=monitor.id,
        status=IncidentStatus.OPEN,
        opened_at=datetime.now(UTC),
        failure_count=3,
        recovery_count=0,
    )
    db_session.add(incident)
    db_session.commit()

    # Success 1: recovery_count=1
    process_incident_state_transition(db_session, monitor, is_healthy=True)
    assert incident.recovery_count == 1
    assert incident.status == IncidentStatus.OPEN

    # Success 2: recovery_count=2
    process_incident_state_transition(db_session, monitor, is_healthy=True)
    assert incident.recovery_count == 2
    assert incident.status == IncidentStatus.OPEN

    # Failure resets progress
    process_incident_state_transition(db_session, monitor, is_healthy=False)
    assert incident.recovery_count == 0
    assert incident.status == IncidentStatus.OPEN
    assert incident.failure_count == 4

    # 3 consecutive successes to resolve
    process_incident_state_transition(db_session, monitor, is_healthy=True)
    assert incident.recovery_count == 1

    process_incident_state_transition(db_session, monitor, is_healthy=True)
    assert incident.recovery_count == 2

    res3 = process_incident_state_transition(db_session, monitor, is_healthy=True)
    assert res3 is not None
    assert res3.recovery_count == 3
    assert res3.status == IncidentStatus.RESOLVED
    assert res3.resolved_at is not None

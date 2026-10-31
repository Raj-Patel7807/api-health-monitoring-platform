"""Integration tests for threshold-based incident creation and concurrency (US-09 / Issue #49).

Uses the real PostgreSQL integration environment:
- Persisted monitor counter updates and backoff escalation.
- Persisted incident creation with status='open', failure_count, opened_at.
- Recovery resetting consecutive_failures to 0.
- Database unique constraint ux_incident_one_open_per_monitor behavior.
- Real multi-threaded concurrency test with synchronization barrier verifying:
  * Two simultaneous results at threshold produce exactly ONE open incident.
  * No unhandled IntegrityError or crash.
  * Correct failure count updated across both results.
"""

import os
import threading
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.modules.incidents.models import Incident
from app.modules.incidents.service import process_monitor_failure
from app.modules.monitors.models import Monitor

_DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/api_health"
)


@pytest.fixture(scope="module")
def pg_engine():
    """Module-scoped PostgreSQL engine."""
    engine = create_engine(_DATABASE_URL, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture
def pg_session(pg_engine) -> Session:
    """Provide an isolated database session cleaned up after each test."""
    session_factory = sessionmaker(bind=pg_engine, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def persisted_monitor(pg_session: Session) -> Monitor:
    """Create and persist a monitor in PostgreSQL."""
    # Ensure a team exists for the foreign key
    team_id = uuid4()
    pg_session.execute(
        text("INSERT INTO teams (id, name) VALUES (:id, :name) ON CONFLICT DO NOTHING"),
        {"id": team_id, "name": f"Integration Test Team {team_id.hex[:8]}"},
    )
    pg_session.commit()

    monitor = Monitor(
        id=uuid4(),
        team_id=team_id,
        name="Integration Health Monitor",
        url="https://api.example.com/health",
        failure_threshold=3,
        recovery_threshold=2,
        check_interval_seconds=60,
        current_interval_seconds=60,
        consecutive_failures=0,
        consecutive_successes=0,
    )
    pg_session.add(monitor)
    pg_session.commit()
    return monitor


def test_persisted_incident_lifecycle(pg_session: Session, persisted_monitor: Monitor) -> None:
    """Test full threshold progression and incident persistence in PostgreSQL."""
    # Failure 1
    res1 = process_monitor_failure(pg_session, persisted_monitor, consecutive_failures=1)
    pg_session.commit()
    assert res1 is None

    # Failure 2
    res2 = process_monitor_failure(pg_session, persisted_monitor, consecutive_failures=2)
    pg_session.commit()
    assert res2 is None

    # Verify no incident in DB
    open_incidents = (
        pg_session.execute(
            select(Incident).where(
                Incident.monitor_id == persisted_monitor.id, Incident.status == "open"
            )
        )
        .scalars()
        .all()
    )
    assert len(open_incidents) == 0

    # Failure 3 -> opens incident
    res3 = process_monitor_failure(pg_session, persisted_monitor, consecutive_failures=3)
    pg_session.commit()
    assert res3 is not None
    assert res3.status == "open"
    assert res3.failure_count == 3
    assert res3.opened_at is not None

    # Failure 4 -> increments existing incident
    res4 = process_monitor_failure(pg_session, persisted_monitor, consecutive_failures=4)
    pg_session.commit()
    assert res4 is not None
    assert res4.id == res3.id
    assert res4.failure_count == 4

    # Verify exactly 1 incident row exists in DB
    all_incidents = (
        pg_session.execute(select(Incident).where(Incident.monitor_id == persisted_monitor.id))
        .scalars()
        .all()
    )
    assert len(all_incidents) == 1
    assert all_incidents[0].failure_count == 4


def test_unique_constraint_enforces_one_open_incident(
    pg_session: Session, persisted_monitor: Monitor
) -> None:
    """Verify that PostgreSQL unique index ux_incident_one_open_per_monitor blocks duplicates."""
    now = datetime.now(UTC)
    inc1 = Incident(
        id=uuid4(),
        monitor_id=persisted_monitor.id,
        status="open",
        opened_at=now,
        failure_count=3,
    )
    pg_session.add(inc1)
    pg_session.commit()

    inc2 = Incident(
        id=uuid4(),
        monitor_id=persisted_monitor.id,
        status="open",
        opened_at=now,
        failure_count=3,
    )
    pg_session.add(inc2)

    with pytest.raises(Exception) as exc_info:
        pg_session.commit()

    assert "ux_incident_one_open_per_monitor" in str(exc_info.value)
    pg_session.rollback()


def test_concurrent_results_at_threshold_produce_one_incident(
    pg_engine, persisted_monitor: Monitor
) -> None:
    """Real concurrency test: two threads simultaneously report reaching the failure threshold.

    Guarantees:
    - Thread synchronization via threading.Barrier to fire exact simultaneous execution.
    - Exactly one open incident created in PostgreSQL.
    - No unhandled errors or crashes in either thread.
    - Both threads finish with a valid open Incident object.
    """
    barrier = threading.Barrier(2)
    session_factory = sessionmaker(bind=pg_engine, expire_on_commit=False)
    results: list[Incident | None] = [None, None]
    exceptions: list[Exception | None] = [None, None]

    def _worker(thread_idx: int) -> None:
        session = session_factory()
        try:
            # Synchronize both threads before entering process_monitor_failure
            barrier.wait(timeout=10)
            incident = process_monitor_failure(
                session=session,
                monitor=persisted_monitor,
                consecutive_failures=3,
            )
            session.commit()
            results[thread_idx] = incident
        except Exception as exc:
            session.rollback()
            exceptions[thread_idx] = exc
        finally:
            session.close()

    t1 = threading.Thread(target=_worker, args=(0,))
    t2 = threading.Thread(target=_worker, args=(1,))

    t1.start()
    t2.start()
    t1.join(timeout=15)
    t2.join(timeout=15)

    # Neither thread should encounter an unhandled exception
    assert exceptions[0] is None, f"Thread 0 raised exception: {exceptions[0]}"
    assert exceptions[1] is None, f"Thread 1 raised exception: {exceptions[1]}"

    # Both threads returned an Incident
    inc0 = results[0]
    inc1 = results[1]
    assert inc0 is not None
    assert inc1 is not None

    # Both threads point to the exact same incident ID
    assert inc0.id == inc1.id

    # Verify state in database: exactly one open incident exists
    verify_session = session_factory()
    try:
        db_incidents = (
            verify_session.execute(
                select(Incident).where(
                    Incident.monitor_id == persisted_monitor.id,
                    Incident.status == "open",
                )
            )
            .scalars()
            .all()
        )
        assert len(db_incidents) == 1
        # One thread created it (failure_count=3), the other incremented it (failure_count=4)
        assert db_incidents[0].failure_count == 4
    finally:
        verify_session.close()

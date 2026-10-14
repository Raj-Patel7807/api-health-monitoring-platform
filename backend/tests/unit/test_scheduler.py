from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.modules.monitors.models import Monitor
from app.modules.monitors.scheduler import find_and_schedule_due_monitors
from app.workers.celery_app import celery_app
from app.workers.tasks import schedule_due_monitors


@pytest.fixture
def db_session() -> Session:
    """Create an isolated in-memory SQLite database session for unit tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()


def test_beat_schedule_and_route_configured() -> None:
    assert "schedule-due-monitors-every-10s" in celery_app.conf.beat_schedule
    entry = celery_app.conf.beat_schedule["schedule-due-monitors-every-10s"]
    assert entry["task"] == "app.workers.tasks.schedule_due_monitors"
    assert entry["schedule"] == 10.0
    assert celery_app.conf.task_routes["app.workers.tasks.schedule_due_monitors"] == {
        "queue": "maintenance"
    }


def test_find_and_schedule_due_monitors_schedules_due_monitor(db_session: Session) -> None:
    now = datetime(2026, 10, 13, 12, 0, 0, tzinfo=UTC)
    team_id = uuid4()
    monitor = Monitor(
        id=uuid4(),
        team_id=team_id,
        name="Production API",
        url="https://api.example.com/health",
        enabled=True,
        check_interval_seconds=60,
        current_interval_seconds=60,
        next_check_at=now - timedelta(seconds=10),
    )
    db_session.add(monitor)
    db_session.commit()

    dispatched: list[str] = []
    result = find_and_schedule_due_monitors(
        session=db_session,
        now=now,
        task_dispatcher=dispatched.append,
    )

    assert result == [str(monitor.id)]
    assert dispatched == [str(monitor.id)]

    db_session.refresh(monitor)
    assert monitor.next_check_at == now + timedelta(seconds=60)


def test_find_and_schedule_due_monitors_handles_null_next_check_at(
    db_session: Session,
) -> None:
    now = datetime(2026, 10, 13, 12, 0, 0, tzinfo=UTC)
    monitor = Monitor(
        id=uuid4(),
        team_id=uuid4(),
        name="New Monitor",
        url="https://api.example.com/health",
        enabled=True,
        check_interval_seconds=30,
        current_interval_seconds=30,
        next_check_at=None,
    )
    db_session.add(monitor)
    db_session.commit()

    dispatched: list[str] = []
    result = find_and_schedule_due_monitors(
        session=db_session,
        now=now,
        task_dispatcher=dispatched.append,
    )

    assert result == [str(monitor.id)]
    db_session.refresh(monitor)
    assert monitor.next_check_at == now + timedelta(seconds=30)


def test_find_and_schedule_due_monitors_skips_future_monitors(db_session: Session) -> None:
    now = datetime(2026, 10, 13, 12, 0, 0, tzinfo=UTC)
    monitor = Monitor(
        id=uuid4(),
        team_id=uuid4(),
        name="Future Monitor",
        url="https://api.example.com/health",
        enabled=True,
        check_interval_seconds=60,
        current_interval_seconds=60,
        next_check_at=now + timedelta(seconds=45),
    )
    db_session.add(monitor)
    db_session.commit()

    dispatched: list[str] = []
    result = find_and_schedule_due_monitors(
        session=db_session,
        now=now,
        task_dispatcher=dispatched.append,
    )

    assert result == []
    assert dispatched == []
    db_session.refresh(monitor)
    assert monitor.next_check_at == now + timedelta(seconds=45)


def test_find_and_schedule_due_monitors_skips_disabled_monitors(db_session: Session) -> None:
    now = datetime(2026, 10, 13, 12, 0, 0, tzinfo=UTC)
    monitor = Monitor(
        id=uuid4(),
        team_id=uuid4(),
        name="Disabled Monitor",
        url="https://api.example.com/health",
        enabled=False,
        check_interval_seconds=60,
        current_interval_seconds=60,
        next_check_at=now - timedelta(seconds=10),
    )
    db_session.add(monitor)
    db_session.commit()

    dispatched: list[str] = []
    result = find_and_schedule_due_monitors(
        session=db_session,
        now=now,
        task_dispatcher=dispatched.append,
    )

    assert result == []
    assert dispatched == []


def test_find_and_schedule_due_monitors_skips_soft_deleted_monitors(
    db_session: Session,
) -> None:
    now = datetime(2026, 10, 13, 12, 0, 0, tzinfo=UTC)
    monitor = Monitor(
        id=uuid4(),
        team_id=uuid4(),
        name="Deleted Monitor",
        url="https://api.example.com/health",
        enabled=True,
        check_interval_seconds=60,
        current_interval_seconds=60,
        next_check_at=now - timedelta(seconds=10),
        deleted_at=now - timedelta(minutes=5),
    )
    db_session.add(monitor)
    db_session.commit()

    dispatched: list[str] = []
    result = find_and_schedule_due_monitors(
        session=db_session,
        now=now,
        task_dispatcher=dispatched.append,
    )

    assert result == []
    assert dispatched == []


def test_find_and_schedule_due_monitors_respects_backoff(db_session: Session) -> None:
    now = datetime(2026, 10, 13, 12, 0, 0, tzinfo=UTC)
    monitor_backed_off = Monitor(
        id=uuid4(),
        team_id=uuid4(),
        name="Backoff Active",
        url="https://api.example.com/health",
        enabled=True,
        check_interval_seconds=60,
        current_interval_seconds=120,
        next_check_at=now - timedelta(seconds=10),
        backoff_until=now + timedelta(seconds=30),
    )
    monitor_backoff_expired = Monitor(
        id=uuid4(),
        team_id=uuid4(),
        name="Backoff Expired",
        url="https://api.example.com/health",
        enabled=True,
        check_interval_seconds=60,
        current_interval_seconds=120,
        next_check_at=now - timedelta(seconds=10),
        backoff_until=now - timedelta(seconds=5),
    )
    db_session.add_all([monitor_backed_off, monitor_backoff_expired])
    db_session.commit()

    dispatched: list[str] = []
    result = find_and_schedule_due_monitors(
        session=db_session,
        now=now,
        task_dispatcher=dispatched.append,
    )

    assert result == [str(monitor_backoff_expired.id)]
    assert dispatched == [str(monitor_backoff_expired.id)]

    db_session.refresh(monitor_backoff_expired)
    assert monitor_backoff_expired.next_check_at == now + timedelta(seconds=120)


def test_find_and_schedule_due_monitors_uses_default_dispatcher(db_session: Session) -> None:
    now = datetime(2026, 10, 13, 12, 0, 0, tzinfo=UTC)
    monitor = Monitor(
        id=uuid4(),
        team_id=uuid4(),
        name="Default Dispatcher Test",
        url="https://api.example.com/health",
        enabled=True,
        check_interval_seconds=60,
        current_interval_seconds=0,
        next_check_at=now,
    )
    db_session.add(monitor)
    db_session.commit()

    with patch("app.modules.monitors.scheduler.celery_app.send_task") as mock_send_task:
        result = find_and_schedule_due_monitors(session=db_session, now=now)
        assert result == [str(monitor.id)]
        mock_send_task.assert_called_once_with(
            "app.workers.tasks.run_health_check",
            args=[str(monitor.id)],
            queue="monitoring",
        )


def test_find_and_schedule_due_monitors_rolls_back_on_exception(db_session: Session) -> None:
    now = datetime(2026, 10, 13, 12, 0, 0, tzinfo=UTC)
    monitor = Monitor(
        id=uuid4(),
        team_id=uuid4(),
        name="Failing Dispatcher Test",
        url="https://api.example.com/health",
        enabled=True,
        check_interval_seconds=60,
        current_interval_seconds=60,
        next_check_at=now,
    )
    db_session.add(monitor)
    db_session.commit()

    def exploding_dispatcher(_: str) -> None:
        raise RuntimeError("Queue connection failed")

    with pytest.raises(RuntimeError, match="Queue connection failed"):
        find_and_schedule_due_monitors(
            session=db_session,
            now=now,
            task_dispatcher=exploding_dispatcher,
        )

    db_session.refresh(monitor)
    # Rollback preserved original next_check_at
    assert monitor.next_check_at == now


def test_schedule_due_monitors_task_runs_within_db_context() -> None:
    mock_session = MagicMock()
    with (
        patch(
            "app.workers.tasks.get_db_session",
            return_value=MagicMock(
                __enter__=MagicMock(return_value=mock_session), __exit__=MagicMock()
            ),
        ),
        patch(
            "app.workers.tasks.find_and_schedule_due_monitors",
            return_value=["test-id"],
        ) as mock_find,
    ):
        result = schedule_due_monitors.run()
        assert result == ["test-id"]
        mock_find.assert_called_once_with(mock_session)


def test_get_db_session_scope() -> None:
    from app.db.session import get_db_session, get_session_factory

    engine = create_engine("sqlite:///:memory:")
    factory = get_session_factory(engine)
    assert factory is not None

    with get_db_session(engine) as session:
        assert session is not None
        assert session.is_active


def test_find_and_schedule_due_monitors_fallback_interval(db_session: Session) -> None:
    now = datetime(2026, 10, 13, 12, 0, 0, tzinfo=UTC)
    monitor = Monitor(
        id=uuid4(),
        team_id=uuid4(),
        name="Fallback Interval",
        url="https://api.example.com/health",
        enabled=True,
        check_interval_seconds=0,
        current_interval_seconds=0,
        next_check_at=now,
    )
    db_session.add(monitor)
    db_session.commit()

    dispatched: list[str] = []
    result = find_and_schedule_due_monitors(
        session=db_session,
        now=now,
        task_dispatcher=dispatched.append,
    )

    assert result == [str(monitor.id)]
    db_session.refresh(monitor)
    assert monitor.next_check_at == now + timedelta(seconds=60)


def test_datetime_utc_bind_param_naive() -> None:
    from app.db.base import DateTimeUTC

    type_dec = DateTimeUTC()
    naive_dt = datetime(2026, 10, 13, 12, 0, 0)
    result = type_dec.process_bind_param(naive_dt, None)
    assert result is not None
    assert result.tzinfo == UTC


def test_restart_does_not_lose_future_schedule(db_session: Session) -> None:
    """Verify that restarting the scheduler/worker preserves all scheduled future checks."""
    now = datetime(2026, 10, 14, 12, 0, 0, tzinfo=UTC)
    future_time = now + timedelta(seconds=120)
    monitor_id = uuid4()
    monitor = Monitor(
        id=monitor_id,
        team_id=uuid4(),
        name="API Monitor",
        url="https://api.example.com/health",
        enabled=True,
        check_interval_seconds=60,
        current_interval_seconds=60,
        next_check_at=future_time,
    )
    db_session.add(monitor)
    db_session.commit()

    # Simulate worker/beat process restart: closing session, re-opening new session
    engine = db_session.get_bind()
    db_session.close()

    # New session after restart
    new_session = Session(engine)
    try:
        persisted = new_session.get(Monitor, monitor_id)
        assert persisted is not None
        assert persisted.next_check_at == future_time

        # Running scheduler tick after restart at 'now'
        dispatched: list[str] = []
        result = find_and_schedule_due_monitors(
            session=new_session,
            now=now,
            task_dispatcher=dispatched.append,
        )
        assert result == []
        assert dispatched == []

        # Future schedule is completely preserved
        new_session.refresh(persisted)
        assert persisted.next_check_at == future_time
    finally:
        new_session.close()


def test_restart_catches_up_due_monitors_missed_during_downtime(db_session: Session) -> None:
    """Verify that after a downtime / crash, scheduler restart immediately detects and
    runs missed checks.
    """
    shutdown_time = datetime(2026, 10, 14, 12, 0, 0, tzinfo=UTC)
    m1_due = shutdown_time + timedelta(seconds=30)
    m2_due = shutdown_time + timedelta(seconds=60)
    m1_id = uuid4()
    m2_id = uuid4()

    monitor1 = Monitor(
        id=m1_id,
        team_id=uuid4(),
        name="Monitor 1",
        url="https://api1.example.com/health",
        enabled=True,
        check_interval_seconds=60,
        current_interval_seconds=60,
        next_check_at=m1_due,
    )
    monitor2 = Monitor(
        id=m2_id,
        team_id=uuid4(),
        name="Monitor 2",
        url="https://api2.example.com/health",
        enabled=True,
        check_interval_seconds=30,
        current_interval_seconds=30,
        next_check_at=m2_due,
    )
    db_session.add_all([monitor1, monitor2])
    db_session.commit()

    # Worker and Beat crash/stop for 10 minutes (600 seconds)
    restart_time = shutdown_time + timedelta(seconds=600)

    # Simulate process restart
    engine = db_session.get_bind()
    db_session.close()
    restart_session = Session(engine)
    try:
        dispatched: list[str] = []
        result = find_and_schedule_due_monitors(
            session=restart_session,
            now=restart_time,
            task_dispatcher=dispatched.append,
        )

        # Both missed monitors must be scheduled immediately
        assert set(result) == {str(m1_id), str(m2_id)}
        assert set(dispatched) == {str(m1_id), str(m2_id)}

        # Both monitors have advanced their schedule forward from restart_time
        reloaded1 = restart_session.get(Monitor, m1_id)
        reloaded2 = restart_session.get(Monitor, m2_id)
        assert reloaded1 is not None and reloaded2 is not None
        assert reloaded1.next_check_at == restart_time + timedelta(seconds=60)
        assert reloaded2.next_check_at == restart_time + timedelta(seconds=30)
    finally:
        restart_session.close()


def test_restart_picks_up_new_monitors_added_during_downtime(db_session: Session) -> None:
    """Verify that newly created monitors with next_check_at=None are scheduled after restart."""
    restart_time = datetime(2026, 10, 14, 12, 0, 0, tzinfo=UTC)
    new_monitor = Monitor(
        id=uuid4(),
        team_id=uuid4(),
        name="Newly Added Monitor",
        url="https://new.example.com/health",
        enabled=True,
        check_interval_seconds=45,
        current_interval_seconds=45,
        next_check_at=None,
    )
    db_session.add(new_monitor)
    db_session.commit()

    dispatched: list[str] = []
    result = find_and_schedule_due_monitors(
        session=db_session,
        now=restart_time,
        task_dispatcher=dispatched.append,
    )

    assert result == [str(new_monitor.id)]
    assert dispatched == [str(new_monitor.id)]
    db_session.refresh(new_monitor)
    assert new_monitor.next_check_at == restart_time + timedelta(seconds=45)

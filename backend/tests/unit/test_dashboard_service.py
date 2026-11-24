"""Unit tests for Dashboard service (US-13).

Covers:
- Status derivation rules (healthy, failing, unknown)
- Summary count accuracy and matching monitor list
- Disabled and soft-deleted monitors being excluded
- Freshness time-window behavior
- Dashboard team isolation
- Query count comparison with 1 and 50 monitors (verifying O(1) query scaling)
"""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models import Team
from app.modules.dashboard.service import (
    derive_monitor_status,
    get_dashboard,
)
from app.modules.incidents.models import Incident
from app.modules.monitors.models import Monitor
from app.modules.results.models import HealthCheckResult

_SQLITE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture()
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(_SQLITE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


def test_derive_monitor_status_rules() -> None:
    """Test all status derivation permutations."""
    recent = datetime.now(UTC)
    assert derive_monitor_status(None, None) == "unknown"
    assert derive_monitor_status(None, uuid4()) == "failing"
    assert derive_monitor_status(recent, None) == "healthy"
    assert derive_monitor_status(recent, uuid4()) == "failing"


@pytest.mark.asyncio
async def test_dashboard_aggregates_and_summary(db_session: AsyncSession) -> None:
    """Test dashboard aggregation with healthy, failing, and unknown monitors."""
    team_id = uuid4()
    team = Team(id=team_id, name="Dashboard Test Team")
    db_session.add(team)

    now = datetime.now(UTC)

    # Monitor 1: Healthy (recent healthy check, no incident)
    m1 = Monitor(
        id=uuid4(),
        team_id=team_id,
        name="Healthy Service",
        url="https://healthy.test",
        method="GET",
        enabled=True,
    )
    # Monitor 2: Failing (recent check failed)
    m2 = Monitor(
        id=uuid4(),
        team_id=team_id,
        name="Failing Service",
        url="https://failing.test",
        method="GET",
        enabled=True,
    )
    # Monitor 3: Open Incident (recent check healthy, but incident open)
    m3 = Monitor(
        id=uuid4(),
        team_id=team_id,
        name="Recovering Service",
        url="https://recovering.test",
        method="GET",
        enabled=True,
    )
    # Monitor 4: Unknown (no check results)
    m4 = Monitor(
        id=uuid4(),
        team_id=team_id,
        name="New Unknown Service",
        url="https://unknown.test",
        method="GET",
        enabled=True,
    )

    db_session.add_all([m1, m2, m3, m4])

    # Add results
    r1 = HealthCheckResult(
        id=uuid4(),
        monitor_id=m1.id,
        checked_at=now - timedelta(minutes=5),
        status="healthy",
        response_time_ms=150,
    )
    r2 = HealthCheckResult(
        id=uuid4(),
        monitor_id=m2.id,
        checked_at=now - timedelta(minutes=2),
        status="failing",
        response_time_ms=900,
    )
    r3 = HealthCheckResult(
        id=uuid4(),
        monitor_id=m3.id,
        checked_at=now - timedelta(minutes=1),
        status="healthy",
        response_time_ms=200,
    )
    inc3 = Incident(
        id=uuid4(),
        monitor_id=m3.id,
        status="open",
        opened_at=now - timedelta(hours=1),
        failure_count=3,
    )

    db_session.add_all([r1, r2, r3, inc3])
    await db_session.commit()

    dashboard = await get_dashboard(db_session, team_id)

    # Summary verification
    assert dashboard.summary.total_monitors == 4
    assert dashboard.summary.healthy == 2
    assert dashboard.summary.failing == 1  # m3 has an open incident
    assert dashboard.summary.unknown == 1  # m4 (no results)
    assert dashboard.summary.open_incidents == 1  # inc3

    # Check that summary counts strictly match the monitors list
    assert (
        dashboard.summary.healthy + dashboard.summary.failing + dashboard.summary.unknown
        == dashboard.summary.total_monitors
    )
    assert len(dashboard.monitors) == 4

    # Ordering check: Failing monitors must be listed first
    assert dashboard.monitors[0].status == "failing"
    assert dashboard.monitors[1].status == "unknown"
    assert dashboard.monitors[2].status == "healthy"
    assert dashboard.monitors[3].status == "healthy"


@pytest.mark.asyncio
async def test_dashboard_excludes_disabled_and_deleted(db_session: AsyncSession) -> None:
    """Disabled and soft-deleted monitors must not be returned on the dashboard."""
    team_id = uuid4()
    db_session.add(Team(id=team_id, name="Exclusion Team"))

    m_active = Monitor(
        id=uuid4(),
        team_id=team_id,
        name="Active Monitor",
        url="https://active.test",
        enabled=True,
    )
    m_disabled = Monitor(
        id=uuid4(),
        team_id=team_id,
        name="Disabled Monitor",
        url="https://disabled.test",
        enabled=False,
    )
    m_deleted = Monitor(
        id=uuid4(),
        team_id=team_id,
        name="Deleted Monitor",
        url="https://deleted.test",
        enabled=True,
        deleted_at=datetime.now(UTC),
    )

    db_session.add_all([m_active, m_disabled, m_deleted])
    await db_session.commit()

    dashboard = await get_dashboard(db_session, team_id)

    assert dashboard.summary.total_monitors == 1
    assert len(dashboard.monitors) == 1
    assert dashboard.monitors[0].id == m_active.id


@pytest.mark.asyncio
async def test_dashboard_freshness_time_window(db_session: AsyncSession) -> None:
    """Results older than the freshness window must classify monitor as unknown."""
    team_id = uuid4()
    db_session.add(Team(id=team_id, name="Freshness Team"))

    now = datetime.now(UTC)

    # Monitor with result within 24h
    m_recent = Monitor(
        id=uuid4(),
        team_id=team_id,
        name="Recent Monitor",
        url="https://recent.test",
        enabled=True,
    )
    # Monitor with result older than 24h
    m_stale = Monitor(
        id=uuid4(),
        team_id=team_id,
        name="Stale Monitor",
        url="https://stale.test",
        enabled=True,
    )

    db_session.add_all([m_recent, m_stale])

    r_recent = HealthCheckResult(
        id=uuid4(),
        monitor_id=m_recent.id,
        checked_at=now - timedelta(hours=2),
        status="healthy",
        response_time_ms=110,
    )
    r_stale = HealthCheckResult(
        id=uuid4(),
        monitor_id=m_stale.id,
        checked_at=now - timedelta(hours=30),  # Stale: > 24 hours ago
        status="healthy",
        response_time_ms=110,
    )

    db_session.add_all([r_recent, r_stale])
    await db_session.commit()

    dashboard = await get_dashboard(db_session, team_id, freshness_window=timedelta(hours=24))

    by_id = {m.id: m for m in dashboard.monitors}
    assert by_id[m_recent.id].status == "healthy"
    assert by_id[m_recent.id].last_checked_at is not None
    assert by_id[m_recent.id].last_response_time_ms == 110

    assert by_id[m_stale.id].status == "unknown"
    assert by_id[m_stale.id].last_checked_at is None
    assert by_id[m_stale.id].last_response_time_ms is None


@pytest.mark.asyncio
async def test_dashboard_team_isolation(db_session: AsyncSession) -> None:
    """Monitors belonging to other teams must never appear on the dashboard."""
    team_a = uuid4()
    team_b = uuid4()
    db_session.add_all([Team(id=team_a, name="Team A"), Team(id=team_b, name="Team B")])

    m_a = Monitor(id=uuid4(), team_id=team_a, name="Monitor A", url="https://a.test", enabled=True)
    m_b = Monitor(id=uuid4(), team_id=team_b, name="Monitor B", url="https://b.test", enabled=True)

    db_session.add_all([m_a, m_b])
    await db_session.commit()

    dashboard_a = await get_dashboard(db_session, team_a)
    assert dashboard_a.summary.total_monitors == 1
    assert dashboard_a.monitors[0].id == m_a.id

    dashboard_b = await get_dashboard(db_session, team_b)
    assert dashboard_b.summary.total_monitors == 1
    assert dashboard_b.monitors[0].id == m_b.id


@pytest.mark.asyncio
async def test_dashboard_query_count_scales_o1(db_session: AsyncSession) -> None:
    """Verify that get_dashboard executes exactly 1 query whether with 1 monitor or 50 monitors."""
    team_1_id = uuid4()
    team_50_id = uuid4()

    db_session.add_all(
        [
            Team(id=team_1_id, name="Team 1"),
            Team(id=team_50_id, name="Team 50"),
        ]
    )
    # Add 1 monitor for team_1
    db_session.add(
        Monitor(
            id=uuid4(),
            team_id=team_1_id,
            name="Single Monitor",
            url="https://single.test",
            enabled=True,
        )
    )
    # Add 50 monitors for team_50
    for i in range(50):
        db_session.add(
            Monitor(
                id=uuid4(),
                team_id=team_50_id,
                name=f"Monitor {i:02d}",
                url=f"https://mon{i}.test",
                enabled=True,
            )
        )
    await db_session.commit()

    query_count = 0

    def _query_listener(conn, cursor, statement, parameters, context, executemany):
        nonlocal query_count
        query_count += 1

    engine = db_session.bind
    assert engine is not None
    event.listen(engine.sync_engine, "before_cursor_execute", _query_listener)

    try:
        # Run for 1 monitor
        query_count = 0
        d1 = await get_dashboard(db_session, team_1_id)
        count_1 = query_count

        # Run for 50 monitors
        query_count = 0
        d50 = await get_dashboard(db_session, team_50_id)
        count_50 = query_count

        assert len(d1.monitors) == 1
        assert len(d50.monitors) == 50

        # Both runs must execute the EXACT same number of queries (O(1))
        assert count_1 == 1, f"Expected 1 query for 1 monitor, got {count_1}"
        assert count_50 == 1, f"Expected 1 query for 50 monitors, got {count_50}"
        assert count_1 == count_50, f"Query count scaled with monitors: {count_1} vs {count_50}"
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", _query_listener)

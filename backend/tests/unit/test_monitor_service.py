"""Unit tests for monitor database service operations (US-02)."""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.modules.monitors import service
from app.modules.monitors.schemas import (
    HttpMethod,
    MonitorCreateRequest,
    MonitorUpdateRequest,
)

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


@pytest.mark.asyncio
async def test_create_monitor_persists_expected_defaults(db_session: AsyncSession) -> None:
    team_id = uuid4()
    req = MonitorCreateRequest(
        name="Checkout API",
        url="https://checkout.example.com/healthz",
        method=HttpMethod.POST,
        check_interval_seconds=120,
        timeout_seconds=15,
        expected_status_code=200,
        failure_threshold=4,
        recovery_threshold=2,
    )
    monitor = await service.create_monitor(db_session, team_id, req)

    assert monitor.id is not None
    assert monitor.team_id == team_id
    assert monitor.name == "Checkout API"
    assert monitor.url == "https://checkout.example.com/healthz"
    assert monitor.method == "POST"
    assert monitor.enabled is True
    assert monitor.check_interval_seconds == 120
    assert monitor.current_interval_seconds == 120
    assert monitor.timeout_seconds == 15
    assert monitor.consecutive_failures == 0
    assert monitor.consecutive_successes == 0
    assert monitor.next_check_at is not None
    assert monitor.deleted_at is None
    assert monitor.created_at is not None
    assert monitor.updated_at is not None


@pytest.mark.asyncio
async def test_get_monitor_by_id_and_team(db_session: AsyncSession) -> None:
    team_a = uuid4()
    team_b = uuid4()
    req = MonitorCreateRequest(name="API A", url="https://a.example.com")
    monitor = await service.create_monitor(db_session, team_a, req)

    # Found on team_a
    found = await service.get_monitor(db_session, team_a, monitor.id)
    assert found is not None
    assert found.id == monitor.id

    # Not found on team_b (team scoping)
    other_team_found = await service.get_monitor(db_session, team_b, monitor.id)
    assert other_team_found is None

    # Unknown ID returns None
    assert await service.get_monitor(db_session, team_a, uuid4()) is None


@pytest.mark.asyncio
async def test_list_monitors_pagination_and_scoping(db_session: AsyncSession) -> None:
    team_a = uuid4()
    team_b = uuid4()

    # Create 5 monitors for team_a
    for i in range(5):
        await service.create_monitor(
            db_session,
            team_a,
            MonitorCreateRequest(name=f"Monitor A{i}", url=f"https://a{i}.example.com"),
        )
    # Create 1 monitor for team_b
    await service.create_monitor(
        db_session,
        team_b,
        MonitorCreateRequest(name="Monitor B", url="https://b.example.com"),
    )

    # Page 1 with page_size=3
    items, total = await service.list_monitors(db_session, team_a, page=1, page_size=3)
    assert total == 5
    assert len(items) == 3

    # Page 2 with page_size=3
    items_p2, total_p2 = await service.list_monitors(db_session, team_a, page=2, page_size=3)
    assert total_p2 == 5
    assert len(items_p2) == 2

    # Team B only sees 1
    items_b, total_b = await service.list_monitors(db_session, team_b, page=1, page_size=10)
    assert total_b == 1
    assert len(items_b) == 1


@pytest.mark.asyncio
async def test_update_monitor_fields_and_interval(db_session: AsyncSession) -> None:
    team_id = uuid4()
    monitor = await service.create_monitor(
        db_session,
        team_id,
        MonitorCreateRequest(name="Original", url="https://original.example.com"),
    )

    update_req = MonitorUpdateRequest(
        name="Updated Name",
        url="https://updated.example.com",
        method=HttpMethod.PATCH,
        enabled=False,
        check_interval_seconds=300,
        timeout_seconds=25,
        expected_status_code=204,
        failure_threshold=5,
        recovery_threshold=3,
        user_agent="UpdatedAgent/1.0",
    )
    updated = await service.update_monitor(db_session, monitor, update_req)

    assert updated.name == "Updated Name"
    assert updated.url == "https://updated.example.com"
    assert updated.method == "PATCH"
    assert updated.enabled is False
    assert updated.check_interval_seconds == 300
    assert updated.current_interval_seconds == 300
    assert updated.timeout_seconds == 25
    assert updated.expected_status_code == 204
    assert updated.failure_threshold == 5
    assert updated.recovery_threshold == 3
    assert updated.user_agent == "UpdatedAgent/1.0"


@pytest.mark.asyncio
async def test_update_monitor_preserves_interval_when_backed_off(db_session: AsyncSession) -> None:
    team_id = uuid4()
    monitor = await service.create_monitor(
        db_session,
        team_id,
        MonitorCreateRequest(name="Backoff Mon", url="https://example.com"),
    )
    # Simulate active backoff
    future_time = datetime.now(UTC) + timedelta(minutes=10)
    monitor.backoff_until = future_time
    monitor.current_interval_seconds = 180

    updated = await service.update_monitor(
        db_session,
        monitor,
        MonitorUpdateRequest(check_interval_seconds=90),
    )
    assert updated.check_interval_seconds == 90
    assert updated.current_interval_seconds == 180  # preserved during active backoff


@pytest.mark.asyncio
async def test_update_monitor_rejects_timeout_greater_than_existing_interval(
    db_session: AsyncSession,
) -> None:
    team_id = uuid4()
    monitor = await service.create_monitor(
        db_session,
        team_id,
        MonitorCreateRequest(name="API", url="https://example.com", check_interval_seconds=30),
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.update_monitor(
            db_session,
            monitor,
            MonitorUpdateRequest(timeout_seconds=35),
        )
    assert exc_info.value.status_code == 422
    assert "cannot exceed check_interval_seconds" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_soft_delete_monitor(db_session: AsyncSession) -> None:
    team_id = uuid4()
    monitor = await service.create_monitor(
        db_session,
        team_id,
        MonitorCreateRequest(name="To Delete", url="https://delete.example.com"),
    )
    monitor_id = monitor.id

    await service.soft_delete_monitor(db_session, monitor)

    assert monitor.deleted_at is not None
    assert monitor.enabled is False

    # Once soft-deleted, get_monitor must return None
    assert await service.get_monitor(db_session, team_id, monitor_id) is None

    # list_monitors must not return the soft-deleted monitor
    items, total = await service.list_monitors(db_session, team_id)
    assert total == 0
    assert len(items) == 0

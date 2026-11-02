"""Database service functions for monitor lifecycle management."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.monitors.models import Monitor
from app.modules.monitors.schemas import MonitorCreateRequest, MonitorUpdateRequest


async def create_monitor(
    db: AsyncSession,
    team_id: UUID,
    data: MonitorCreateRequest,
) -> Monitor:
    """Create and persist a new Monitor scoped to *team_id*."""
    now = datetime.now(UTC)
    monitor = Monitor(
        team_id=team_id,
        name=data.name,
        url=data.url,
        method=data.method.value,
        enabled=data.enabled,
        check_interval_seconds=data.check_interval_seconds,
        current_interval_seconds=data.check_interval_seconds,
        timeout_seconds=data.timeout_seconds,
        failure_threshold=data.failure_threshold,
        recovery_threshold=data.recovery_threshold,
        consecutive_failures=0,
        consecutive_successes=0,
        expected_status_code=data.expected_status_code,
        user_agent=data.user_agent,
        next_check_at=now,  # AC-02.6: eligible for scheduled checks immediately
        created_at=now,
        updated_at=now,
    )
    db.add(monitor)
    await db.flush()
    await db.refresh(monitor)
    return monitor


async def get_monitor(
    db: AsyncSession,
    team_id: UUID,
    monitor_id: UUID,
) -> Monitor | None:
    """Retrieve an active (non-soft-deleted) monitor scoped to *team_id*."""
    stmt = select(Monitor).where(
        Monitor.id == monitor_id,
        Monitor.team_id == team_id,
        Monitor.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_monitors(
    db: AsyncSession,
    team_id: UUID,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Monitor], int]:
    """Return paginated active monitors and total count scoped to *team_id*."""
    base_filter = [
        Monitor.team_id == team_id,
        Monitor.deleted_at.is_(None),
    ]

    # Total count
    count_stmt = select(func.count(Monitor.id)).where(*base_filter)
    count_res = await db.execute(count_stmt)
    total = count_res.scalar_one() or 0

    # Paginated rows
    offset = (page - 1) * page_size
    query_stmt = (
        select(Monitor)
        .where(*base_filter)
        .order_by(Monitor.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    items_res = await db.execute(query_stmt)
    items = list(items_res.scalars().all())

    return items, total


async def update_monitor(
    db: AsyncSession,
    monitor: Monitor,
    data: MonitorUpdateRequest,
) -> Monitor:
    """Partially update a monitor, validating merged timeout/interval constraints."""
    target_interval = (
        data.check_interval_seconds
        if data.check_interval_seconds is not None
        else monitor.check_interval_seconds
    )
    target_timeout = (
        data.timeout_seconds if data.timeout_seconds is not None else monitor.timeout_seconds
    )

    if target_timeout > target_interval:
        raise HTTPException(
            status_code=422,
            detail=(
                f"timeout_seconds ({target_timeout}) cannot exceed "
                f"check_interval_seconds ({target_interval})."
            ),
        )

    if data.name is not None:
        monitor.name = data.name
    if data.url is not None:
        monitor.url = data.url
    if data.method is not None:
        monitor.method = data.method.value
    if data.enabled is not None:
        monitor.enabled = data.enabled
    if data.check_interval_seconds is not None:
        if monitor.backoff_until is None or monitor.backoff_until <= datetime.now(UTC):
            monitor.current_interval_seconds = data.check_interval_seconds
        monitor.check_interval_seconds = data.check_interval_seconds
    if data.timeout_seconds is not None:
        monitor.timeout_seconds = data.timeout_seconds
    if data.expected_status_code is not None:
        monitor.expected_status_code = data.expected_status_code
    if data.failure_threshold is not None:
        monitor.failure_threshold = data.failure_threshold
    if data.recovery_threshold is not None:
        monitor.recovery_threshold = data.recovery_threshold
    if data.user_agent is not None:
        monitor.user_agent = data.user_agent

    monitor.updated_at = datetime.now(UTC)
    await db.flush()
    await db.refresh(monitor)
    return monitor


async def soft_delete_monitor(
    db: AsyncSession,
    monitor: Monitor,
) -> None:
    """Soft delete a monitor by setting deleted_at and disabling it."""
    now = datetime.now(UTC)
    monitor.deleted_at = now
    monitor.enabled = False
    monitor.updated_at = now
    await db.flush()

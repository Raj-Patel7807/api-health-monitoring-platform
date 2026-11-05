
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.results.models import HealthCheckResult


MAX_RANGE_DAYS = 31
MAX_PAGE_SIZE = 100


async def list_health_check_results(
    db: AsyncSession,
    monitor_id: UUID,
    page: int = 1,
    page_size: int = 20,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    result_status: str | None = None,
) -> tuple[list[HealthCheckResult], int, datetime, datetime]:
    """Return filtered and paginated results for one monitor."""

    now = datetime.now(UTC)

    # Default to the last 24 hours.
    effective_end = end_time or now
    effective_start = start_time or (effective_end - timedelta(hours=24))

    # Require timezone-aware timestamps.
    if (
        effective_start.tzinfo is None
        or effective_start.utcoffset() is None
        or effective_end.tzinfo is None
        or effective_end.utcoffset() is None
    ):
        raise HTTPException(
            status_code=422,
            detail="start_time and end_time must include a timezone.",
        )

    if effective_start >= effective_end:
        raise HTTPException(
            status_code=422,
            detail="start_time must be earlier than end_time.",
        )

    if effective_end - effective_start > timedelta(days=MAX_RANGE_DAYS):
        raise HTTPException(
            status_code=422,
            detail="The requested time range cannot exceed 31 days.",
        )

    if page < 1:
        raise HTTPException(
            status_code=422,
            detail="page must be at least 1.",
        )

    if page_size < 1 or page_size > MAX_PAGE_SIZE:
        raise HTTPException(
            status_code=422,
            detail="page_size must be between 1 and 100.",
        )

        filters = [
        HealthCheckResult.monitor_id == monitor_id,
        HealthCheckResult.checked_at >= effective_start,
        HealthCheckResult.checked_at <= effective_end,
        HealthCheckResult.status.in_(["healthy", "failing"]),
    ]
    if result_status is not None:
        if result_status not in {"healthy", "failing"}:
            raise HTTPException(
                status_code=422,
                detail="status must be either 'healthy' or 'failing'.",
            )
        filters.append(HealthCheckResult.status == result_status)

    count_stmt = (
        select(func.count())
        .select_from(HealthCheckResult)
        .where(*filters)
    )
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    offset = (page - 1) * page_size

    results_stmt = (
        select(HealthCheckResult)
        .where(*filters)
        .order_by(
            HealthCheckResult.checked_at.desc(),
            HealthCheckResult.id.desc(),
        )
        .offset(offset)
        .limit(page_size)
    )

    results_result = await db.execute(results_stmt)
    items = list(results_result.scalars().all())

    return items, total, effective_start, effective_end

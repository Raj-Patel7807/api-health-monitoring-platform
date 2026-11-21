from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.modules.results.service import list_health_check_results


def make_db():
    """Create a mocked async database session."""
    db = MagicMock()

    count_result = MagicMock()
    count_result.scalar_one.return_value = 2

    rows_result = MagicMock()
    rows_result.scalars.return_value.all.return_value = ["result1", "result2"]

    db.execute = AsyncMock(side_effect=[count_result, rows_result])

    return db


@pytest.mark.asyncio
async def test_default_time_range_is_last_24_hours():
    db = make_db()

    _, _, start, end = await list_health_check_results(
        db=db,
        monitor_id=uuid4(),
    )

    assert end - start == timedelta(hours=24)


@pytest.mark.asyncio
async def test_returns_results_and_total_count():
    db = make_db()

    items, total, _, _ = await list_health_check_results(
        db=db,
        monitor_id=uuid4(),
    )

    assert items == ["result1", "result2"]
    assert total == 2
    assert db.execute.await_count == 2


@pytest.mark.asyncio
async def test_passes_filters_and_pagination_to_query():
    db = make_db()
    monitor_id = uuid4()
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = datetime(2026, 1, 10, tzinfo=UTC)

    await list_health_check_results(
        db=db,
        monitor_id=monitor_id,
        page=2,
        page_size=10,
        start_time=start,
        end_time=end,
        result_status="failing",
    )

    count_query = str(db.execute.await_args_list[0].args[0])
    results_query = str(db.execute.await_args_list[1].args[0])

    assert "health_check_results.monitor_id" in count_query
    assert "health_check_results.checked_at" in count_query
    assert "health_check_results.status" in count_query
    assert "ORDER BY" in results_query
    assert "LIMIT" in results_query
    assert "OFFSET" in results_query


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["start_time", "end_time"])
async def test_rejects_timezone_naive_datetime(field):
    db = make_db()
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = datetime(2026, 1, 2, tzinfo=UTC)

    if field == "start_time":
        start = datetime(2026, 1, 1)
    else:
        end = datetime(2026, 1, 2)

    with pytest.raises(HTTPException) as exc:
        await list_health_check_results(
            db=db,
            monitor_id=uuid4(),
            start_time=start,
            end_time=end,
        )

    assert exc.value.status_code == 422
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_rejects_start_time_after_end_time():
    db = make_db()

    with pytest.raises(HTTPException) as exc:
        await list_health_check_results(
            db=db,
            monitor_id=uuid4(),
            start_time=datetime(2026, 1, 5, tzinfo=UTC),
            end_time=datetime(2026, 1, 1, tzinfo=UTC),
        )

    assert exc.value.status_code == 422
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_rejects_time_range_over_31_days():
    db = make_db()

    with pytest.raises(HTTPException) as exc:
        await list_health_check_results(
            db=db,
            monitor_id=uuid4(),
            start_time=datetime(2026, 1, 1, tzinfo=UTC),
            end_time=datetime(2026, 2, 2, tzinfo=UTC),
        )

    assert exc.value.status_code == 422
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_rejects_page_less_than_one():
    db = make_db()

    with pytest.raises(HTTPException) as exc:
        await list_health_check_results(
            db=db,
            monitor_id=uuid4(),
            page=0,
        )

    assert exc.value.status_code == 422
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("page_size", [0, 101])
async def test_rejects_invalid_page_size(page_size):
    db = make_db()

    with pytest.raises(HTTPException) as exc:
        await list_health_check_results(
            db=db,
            monitor_id=uuid4(),
            page_size=page_size,
        )

    assert exc.value.status_code == 422
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_rejects_invalid_result_status():
    db = make_db()

    with pytest.raises(HTTPException) as exc:
        await list_health_check_results(
            db=db,
            monitor_id=uuid4(),
            result_status="degraded",
        )

    assert exc.value.status_code == 422
    db.execute.assert_not_awaited()

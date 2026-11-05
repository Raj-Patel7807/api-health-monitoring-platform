
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.modules.results.recorder import (
    BODY_EXCERPT_MAX_CHARS,
    build_result_row,
    record_check_result,
)


def make_check_result(**overrides):
    """Create a simple health-check result for recorder tests."""
    values = {
        "status": "healthy",
        "checked_at": datetime.now(UTC),
        "http_status_code": 200,
        "response_time_ms": 120,
        "timeout": False,
        "connection_error": False,
        "ssl_error": False,
        "error_message": None,
        "body_excerpt": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_build_result_row_saves_healthy_result():
    monitor_id = uuid4()
    result = make_check_result()

    row = build_result_row(result, monitor_id)

    assert row.monitor_id == monitor_id
    assert row.status == "healthy"
    assert row.http_status_code == 200
    assert row.response_time_ms == 120
    assert row.response_body_excerpt == ""
    assert row.timeout is False
    assert row.connection_error is False
    assert row.ssl_error is False


def test_build_result_row_saves_failing_response_excerpt():
    result = make_check_result(
        status="failing",
        http_status_code=500,
        response_time_ms=250,
        body_excerpt="Internal Server Error",
    )

    row = build_result_row(result, uuid4())

    assert row.status == "failing"
    assert row.http_status_code == 500
    assert row.response_time_ms == 250
    assert row.response_body_excerpt == "Internal Server Error"


def test_response_excerpt_is_limited_to_500_characters():
    result = make_check_result(
        status="failing",
        body_excerpt="X" * 700,
    )

    row = build_result_row(result, uuid4())

    assert len(row.response_body_excerpt) == BODY_EXCERPT_MAX_CHARS
    assert len(row.response_body_excerpt) == 500


@pytest.mark.parametrize(
    "failure_flag",
    ["timeout", "connection_error", "ssl_error"],
)
def test_transport_failures_do_not_save_http_status_or_response_time(
    failure_flag,
):
    result = make_check_result(
        status="failing",
        http_status_code=500,
        response_time_ms=300,
        **{failure_flag: True},
    )

    row = build_result_row(result, uuid4())

    assert row.status == "failing"
    assert row.http_status_code is None
    assert row.response_time_ms is None
    assert getattr(row, failure_flag) is True


def test_build_result_row_removes_null_characters():
    result = make_check_result(
        status="failing",
        error_message="Connection\x00failed",
        body_excerpt="Response\x00body",
    )

    row = build_result_row(result, uuid4())

    assert row.error_message == "Connectionfailed"
    assert row.response_body_excerpt == "Responsebody"


def test_build_result_row_rejects_degraded_status():
    result = make_check_result(status="degraded")

    with pytest.raises(ValueError, match="Invalid health check status"):
        build_result_row(result, uuid4())


def test_record_check_result_adds_row_to_session():
    session = MagicMock()
    monitor_id = uuid4()
    result = make_check_result()

    row = record_check_result(session, result, monitor_id)

    session.add.assert_called_once_with(row)
    assert row.monitor_id == monitor_id
    assert row.status == "healthy"

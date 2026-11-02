"""Unit tests for monitor Pydantic schemas and validation rules (US-02)."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.modules.monitors.schemas import (
    HttpMethod,
    MonitorCreateRequest,
    MonitorUpdateRequest,
)


def test_monitor_create_valid_defaults() -> None:
    req = MonitorCreateRequest(
        name="Production API",
        url="https://api.example.com/health",
    )
    assert req.name == "Production API"
    assert req.url == "https://api.example.com/health"
    assert req.method == HttpMethod.GET
    assert req.check_interval_seconds == 60
    assert req.timeout_seconds == 10
    assert req.expected_status_code == 200
    assert req.failure_threshold == 3
    assert req.recovery_threshold == 2
    assert req.enabled is True
    assert req.user_agent == "APIMonitor/1.0"
    assert req.team_id is None


def test_monitor_create_all_fields_and_method_normalization() -> None:
    team_id = uuid4()
    req = MonitorCreateRequest(
        name="  Auth Service  ",
        url="http://auth.internal:8080/v1/ping?foo=bar",
        method="post",  # type: ignore[arg-type]
        check_interval_seconds=120,
        timeout_seconds=15,
        expected_status_code=204,
        failure_threshold=5,
        recovery_threshold=3,
        enabled=False,
        user_agent="CustomAgent/2.0",
        team_id=team_id,
    )
    assert req.name == "Auth Service"
    assert req.method == HttpMethod.POST
    assert req.check_interval_seconds == 120
    assert req.timeout_seconds == 15
    assert req.expected_status_code == 204
    assert req.team_id == team_id


@pytest.mark.parametrize(
    "bad_name",
    ["", "   ", "\t\n"],
)
def test_monitor_create_rejects_empty_or_whitespace_name(bad_name: str) -> None:
    with pytest.raises(ValidationError) as exc_info:
        MonitorCreateRequest(name=bad_name, url="https://api.example.com/health")
    error_str = str(exc_info.value)
    assert (
        "Name cannot be empty or whitespace only" in error_str
        or "String should have at least 1 character" in error_str
    )


def test_monitor_create_rejects_overlong_name() -> None:
    with pytest.raises(ValidationError):
        MonitorCreateRequest(name="A" * 151, url="https://api.example.com/health")


@pytest.mark.parametrize(
    "bad_url, error_match",
    [
        ("", "URL cannot be empty"),
        ("   ", "URL cannot be empty"),
        ("ftp://ftp.example.com/file", "must have http or https scheme"),
        ("javascript:alert(1)", "must have http or https scheme"),
        ("http://", "must have a valid host"),
        ("https://", "must have a valid host"),
        ("not-a-valid-url", "must have http or https scheme"),
    ],
)
def test_monitor_create_rejects_invalid_urls(bad_url: str, error_match: str) -> None:
    with pytest.raises(ValidationError) as exc_info:
        MonitorCreateRequest(name="API", url=bad_url)
    assert error_match in str(exc_info.value)


def test_monitor_create_rejects_overlong_url() -> None:
    long_url = "https://api.example.com/" + ("a" * 2050)
    with pytest.raises(ValidationError) as exc_info:
        MonitorCreateRequest(name="API", url=long_url)
    assert "cannot exceed 2048 characters" in str(
        exc_info.value
    ) or "String should have at most" in str(exc_info.value)


def test_monitor_create_rejects_invalid_method() -> None:
    with pytest.raises(ValidationError) as exc_info:
        MonitorCreateRequest(name="API", url="https://api.example.com", method="CONNECT")  # type: ignore[arg-type]
    assert "Invalid HTTP method" in str(exc_info.value)


def test_monitor_create_rejects_timeout_greater_than_interval() -> None:
    with pytest.raises(ValidationError) as exc_info:
        MonitorCreateRequest(
            name="API",
            url="https://api.example.com",
            check_interval_seconds=30,
            timeout_seconds=35,
        )
    assert "timeout_seconds (35) cannot exceed check_interval_seconds (30)" in str(exc_info.value)


@pytest.mark.parametrize("status_code", [99, 600, 0, -1])
def test_monitor_create_rejects_out_of_range_status_code(status_code: int) -> None:
    with pytest.raises(ValidationError):
        MonitorCreateRequest(
            name="API", url="https://api.example.com", expected_status_code=status_code
        )


@pytest.mark.parametrize("interval", [0, -1, 86401])
def test_monitor_create_rejects_invalid_interval(interval: int) -> None:
    with pytest.raises(ValidationError):
        MonitorCreateRequest(
            name="API", url="https://api.example.com", check_interval_seconds=interval
        )


@pytest.mark.parametrize("timeout", [0, -5, 301])
def test_monitor_create_rejects_invalid_timeout(timeout: int) -> None:
    with pytest.raises(ValidationError):
        MonitorCreateRequest(name="API", url="https://api.example.com", timeout_seconds=timeout)


@pytest.mark.parametrize("threshold", [0, -1, 101])
def test_monitor_create_rejects_invalid_thresholds(threshold: int) -> None:
    with pytest.raises(ValidationError):
        MonitorCreateRequest(name="API", url="https://api.example.com", failure_threshold=threshold)
    with pytest.raises(ValidationError):
        MonitorCreateRequest(
            name="API", url="https://api.example.com", recovery_threshold=threshold
        )


# ---------------------------------------------------------------------------
# MonitorUpdateRequest tests
# ---------------------------------------------------------------------------


def test_monitor_update_partial_valid() -> None:
    update = MonitorUpdateRequest(
        name="New Name",
        method="put",  # type: ignore[arg-type]
        check_interval_seconds=300,
        timeout_seconds=20,
    )
    assert update.name == "New Name"
    assert update.method == HttpMethod.PUT
    assert update.check_interval_seconds == 300
    assert update.timeout_seconds == 20
    assert update.url is None


def test_monitor_update_empty_whitespace_name_rejected() -> None:
    with pytest.raises(ValidationError):
        MonitorUpdateRequest(name="   ")


def test_monitor_update_invalid_url_rejected() -> None:
    with pytest.raises(ValidationError):
        MonitorUpdateRequest(url="ftp://bad")


def test_monitor_update_invalid_method_rejected() -> None:
    with pytest.raises(ValidationError):
        MonitorUpdateRequest(method="INVALID")  # type: ignore[arg-type]


def test_monitor_update_timeout_exceeding_interval_rejected() -> None:
    with pytest.raises(ValidationError) as exc_info:
        MonitorUpdateRequest(check_interval_seconds=30, timeout_seconds=40)
    assert "timeout_seconds (40) cannot exceed check_interval_seconds (30)" in str(exc_info.value)

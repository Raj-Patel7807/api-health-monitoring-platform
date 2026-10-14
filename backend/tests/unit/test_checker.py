"""Unit tests for the health-check execution module.

Tests cover all acceptance criteria:
  AC-06.1 — healthy response (expected status code received)
  AC-06.2 — wrong status code classified as failure
  AC-06.3 — timeout classified as timeout failure
  AC-06.4 — connection failure classified as connection error
  AC-06.5 — SSL/TLS failure classified as ssl_error
  AC-06.6 — a single failure only increments consecutive_failures, no incident

All HTTP calls are mocked — no real network traffic, no real DB required.
The in-memory SQLite engine is re-used from the existing scheduler test pattern.
"""

import ssl
from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.modules.monitors.checker import (
    CheckResult,
    check_monitor_by_id,
    execute_http_check,
    update_monitor_counters,
)
from app.modules.monitors.models import Monitor

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

MONITOR_URL = "https://api.example.com/health"
MONITOR_METHOD = "GET"
EXPECTED_STATUS = 200
TIMEOUT_SECONDS = 10
USER_AGENT = "APIMonitor/1.0"
MONITOR_ID = str(uuid4())


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    """Isolated in-memory SQLite session — no PostgreSQL required."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()


@pytest.fixture()
def base_monitor(db_session: Session) -> Monitor:
    """A fully enabled monitor inserted into the in-memory database."""
    monitor = Monitor(
        id=uuid4(),
        team_id=uuid4(),
        name="Test API",
        url=MONITOR_URL,
        method=MONITOR_METHOD,
        enabled=True,
        check_interval_seconds=60,
        current_interval_seconds=60,
        timeout_seconds=TIMEOUT_SECONDS,
        expected_status_code=EXPECTED_STATUS,
        user_agent=USER_AGENT,
        consecutive_failures=0,
        consecutive_successes=0,
    )
    db_session.add(monitor)
    db_session.commit()
    return monitor


# ---------------------------------------------------------------------------
# Helper: build a fake httpx.Response
# ---------------------------------------------------------------------------


def _fake_response(status_code: int) -> httpx.Response:
    """Return a minimal httpx.Response with the given status code."""
    return httpx.Response(status_code=status_code, content=b"")


# ===========================================================================
# execute_http_check  (pure HTTP layer — no DB)
# ===========================================================================


class TestExecuteHttpCheck:
    """Tests for execute_http_check — mocks httpx.Client.request."""

    def _run(
        self,
        mock_client: MagicMock,
        url: str = MONITOR_URL,
        method: str = MONITOR_METHOD,
        expected: int = EXPECTED_STATUS,
        timeout: int = TIMEOUT_SECONDS,
        user_agent: str = USER_AGENT,
        monitor_id: str = MONITOR_ID,
    ) -> CheckResult:
        with patch("app.modules.monitors.checker.httpx.Client") as mock_cls:
            ctx = mock_cls.return_value.__enter__.return_value
            ctx.request.side_effect = mock_client
            return execute_http_check(url, method, expected, timeout, user_agent, monitor_id)

    # AC-06.1 — expected status → healthy
    def test_expected_status_code_is_healthy(self) -> None:
        def fake_request(*args: object, **kwargs: object) -> httpx.Response:
            return _fake_response(200)

        result = self._run(fake_request)

        assert result.status == "healthy"
        assert result.http_status_code == 200
        assert result.timeout is False
        assert result.connection_error is False
        assert result.ssl_error is False
        assert result.error_message is None
        assert result.response_time_ms >= 0

    # AC-06.2 — wrong status code → failing
    def test_wrong_status_code_is_failing(self) -> None:
        def fake_request(*args: object, **kwargs: object) -> httpx.Response:
            return _fake_response(500)

        result = self._run(fake_request)

        assert result.status == "failing"
        assert result.http_status_code == 500
        assert result.timeout is False
        assert result.connection_error is False
        assert result.ssl_error is False
        assert result.error_message is not None
        assert "500" in result.error_message

    # AC-06.2 — 404 is also a wrong status code
    def test_404_wrong_status_code_is_failing(self) -> None:
        def fake_request(*args: object, **kwargs: object) -> httpx.Response:
            return _fake_response(404)

        result = self._run(fake_request, expected=200)

        assert result.status == "failing"
        assert result.http_status_code == 404

    # AC-06.3 — ReadTimeout → timeout failure
    def test_read_timeout_is_timeout_failure(self) -> None:
        def fake_request(*args: object, **kwargs: object) -> httpx.Response:
            raise httpx.ReadTimeout("Read timeout", request=MagicMock())

        result = self._run(fake_request)

        assert result.status == "failing"
        assert result.timeout is True
        assert result.connection_error is False
        assert result.ssl_error is False
        assert result.error_message is not None

    # AC-06.3 — ConnectTimeout → timeout failure
    def test_connect_timeout_is_timeout_failure(self) -> None:
        def fake_request(*args: object, **kwargs: object) -> httpx.Response:
            raise httpx.ConnectTimeout("Connect timeout", request=MagicMock())

        result = self._run(fake_request)

        assert result.status == "failing"
        assert result.timeout is True
        assert result.connection_error is False

    # AC-06.4 — ConnectError without SSL cause → connection failure
    def test_connection_error_is_connection_failure(self) -> None:
        def fake_request(*args: object, **kwargs: object) -> httpx.Response:
            raise httpx.ConnectError("Connection refused")

        result = self._run(fake_request)

        assert result.status == "failing"
        assert result.connection_error is True
        assert result.ssl_error is False
        assert result.timeout is False
        assert result.error_message is not None

    # AC-06.5 — ConnectError with ssl.SSLError cause → SSL failure
    def test_ssl_error_via_ssl_cause_is_ssl_failure(self) -> None:
        def fake_request(*args: object, **kwargs: object) -> httpx.Response:
            ssl_exc = ssl.SSLError("certificate verify failed")
            raise httpx.ConnectError("SSL handshake failed") from ssl_exc

        result = self._run(fake_request)

        assert result.status == "failing"
        assert result.ssl_error is True
        assert result.connection_error is False
        assert result.timeout is False
        assert result.error_message is not None

    # AC-06.5 — ConnectError with "SSL" in message → SSL failure
    def test_ssl_error_via_message_is_ssl_failure(self) -> None:
        def fake_request(*args: object, **kwargs: object) -> httpx.Response:
            raise httpx.ConnectError("SSL: CERTIFICATE_VERIFY_FAILED")

        result = self._run(fake_request)

        assert result.status == "failing"
        assert result.ssl_error is True
        assert result.connection_error is False

    # AC-06.4 — NetworkError (e.g. connection reset) → connection failure
    def test_network_error_is_connection_failure(self) -> None:
        def fake_request(*args: object, **kwargs: object) -> httpx.Response:
            raise httpx.NetworkError("Connection reset by peer")

        result = self._run(fake_request)

        assert result.status == "failing"
        assert result.connection_error is True
        assert result.timeout is False
        assert result.ssl_error is False

    # Custom expected status (e.g. 201)
    def test_custom_expected_status_code_is_healthy(self) -> None:
        def fake_request(*args: object, **kwargs: object) -> httpx.Response:
            return _fake_response(201)

        result = self._run(fake_request, expected=201)

        assert result.status == "healthy"
        assert result.http_status_code == 201

    # User-Agent header is sent
    def test_user_agent_header_is_sent(self) -> None:
        captured_headers: dict[str, str] = {}

        def fake_request(
            method: str, url: str, headers: dict[str, str] | None = None, **kwargs: object
        ) -> httpx.Response:
            if headers:
                captured_headers.update(headers)
            return _fake_response(200)

        self._run(fake_request, user_agent="MyAgent/2.0")
        assert captured_headers.get("User-Agent") == "MyAgent/2.0"

    # response_time_ms is non-negative
    def test_response_time_ms_is_non_negative(self) -> None:
        def fake_request(*args: object, **kwargs: object) -> httpx.Response:
            return _fake_response(200)

        result = self._run(fake_request)
        assert result.response_time_ms >= 0

    # AC-06.2 — redirects are not followed, so a 301 is a wrong status code
    def test_redirect_status_is_failing(self) -> None:
        def fake_request(*args: object, **kwargs: object) -> httpx.Response:
            return _fake_response(301)

        result = self._run(fake_request)

        assert result.status == "failing"
        assert result.http_status_code == 301
        assert result.timeout is False
        assert result.connection_error is False
        assert result.ssl_error is False

    # The monitor's method and URL are what actually get requested
    def test_method_and_url_are_passed_to_client(self) -> None:
        captured: dict[str, str] = {}

        def fake_request(method: str, url: str, **kwargs: object) -> httpx.Response:
            captured["method"] = method
            captured["url"] = url
            return _fake_response(200)

        self._run(fake_request, url="https://api.example.com/ping", method="HEAD")

        assert captured == {"method": "HEAD", "url": "https://api.example.com/ping"}

    # AC-06.3 — PoolTimeout is also a timeout failure
    def test_pool_timeout_is_timeout_failure(self) -> None:
        def fake_request(*args: object, **kwargs: object) -> httpx.Response:
            raise httpx.PoolTimeout("Pool timeout", request=MagicMock())

        result = self._run(fake_request)

        assert result.status == "failing"
        assert result.timeout is True
        assert result.connection_error is False
        assert result.ssl_error is False

    # AC-06.3 — the timeout message names the configured limit
    def test_timeout_message_includes_configured_seconds(self) -> None:
        def fake_request(*args: object, **kwargs: object) -> httpx.Response:
            raise httpx.ReadTimeout("Read timeout", request=MagicMock())

        result = self._run(fake_request, timeout=7)

        assert result.error_message is not None
        assert "7s" in result.error_message

    # DR-2 — certificate verification is on and the monitor timeout is applied
    def test_client_is_created_with_verify_and_timeout(self) -> None:
        with patch("app.modules.monitors.checker.httpx.Client") as mock_cls:
            ctx = mock_cls.return_value.__enter__.return_value
            ctx.request.return_value = _fake_response(200)
            execute_http_check(MONITOR_URL, "GET", 200, 7, USER_AGENT, MONITOR_ID)

        mock_cls.assert_called_once_with(timeout=7, verify=True)

    # AC-06.5 — SSL failures have a distinguishable message
    def test_ssl_error_message_is_prefixed(self) -> None:
        def fake_request(*args: object, **kwargs: object) -> httpx.Response:
            raise httpx.ConnectError("SSL: CERTIFICATE_VERIFY_FAILED")

        result = self._run(fake_request)

        assert result.error_message is not None
        assert result.error_message.startswith("SSL/TLS error")

    # The result carries the monitor id it was run for
    def test_result_carries_monitor_id(self) -> None:
        def fake_request(*args: object, **kwargs: object) -> httpx.Response:
            return _fake_response(200)

        result = self._run(fake_request, monitor_id="abc-123")

        assert result.monitor_id == "abc-123"


# ===========================================================================
# update_monitor_counters  (pure logic, no I/O)
# ===========================================================================


class TestUpdateMonitorCounters:
    """Tests for the pure counter update helper."""

    def _make_monitor(self, failures: int = 0, successes: int = 0) -> Monitor:
        return Monitor(
            consecutive_failures=failures,
            consecutive_successes=successes,
        )

    # Success resets failures and increments successes
    def test_success_resets_failures_and_increments_successes(self) -> None:
        monitor = self._make_monitor(failures=3, successes=0)
        result = CheckResult(monitor_id=MONITOR_ID, status="healthy")

        update_monitor_counters(monitor, result)

        assert monitor.consecutive_failures == 0
        assert monitor.consecutive_successes == 1

    # Failure resets successes and increments failures
    def test_failure_increments_failures_and_resets_successes(self) -> None:
        monitor = self._make_monitor(failures=0, successes=5)
        result = CheckResult(monitor_id=MONITOR_ID, status="failing")

        update_monitor_counters(monitor, result)

        assert monitor.consecutive_failures == 1
        assert monitor.consecutive_successes == 0

    # AC-06.6 — a single failure should NOT reset the counter to > 1
    def test_single_failure_increments_by_one_only(self) -> None:
        monitor = self._make_monitor(failures=0, successes=0)
        result = CheckResult(monitor_id=MONITOR_ID, status="failing")

        update_monitor_counters(monitor, result)

        assert monitor.consecutive_failures == 1  # not 2, not 3

    # Consecutive failures accumulate
    def test_consecutive_failures_accumulate(self) -> None:
        monitor = self._make_monitor(failures=2, successes=0)
        result = CheckResult(monitor_id=MONITOR_ID, status="failing")

        update_monitor_counters(monitor, result)

        assert monitor.consecutive_failures == 3

    # After recovery successes accumulate
    def test_consecutive_successes_accumulate_after_recovery(self) -> None:
        monitor = self._make_monitor(failures=0, successes=1)
        result = CheckResult(monitor_id=MONITOR_ID, status="healthy")

        update_monitor_counters(monitor, result)

        assert monitor.consecutive_successes == 2
        assert monitor.consecutive_failures == 0

    # Mixed sequence: fail, fail, succeed, fail
    def test_mixed_sequence_tracks_streaks_correctly(self) -> None:
        monitor = self._make_monitor()
        failing = CheckResult(monitor_id=MONITOR_ID, status="failing")
        healthy = CheckResult(monitor_id=MONITOR_ID, status="healthy")

        update_monitor_counters(monitor, failing)
        update_monitor_counters(monitor, failing)
        assert monitor.consecutive_failures == 2

        update_monitor_counters(monitor, healthy)
        assert monitor.consecutive_failures == 0
        assert monitor.consecutive_successes == 1

        update_monitor_counters(monitor, failing)
        assert monitor.consecutive_failures == 1
        assert monitor.consecutive_successes == 0


# ===========================================================================
# check_monitor_by_id  (orchestrator — uses injected db_session)
# ===========================================================================


class TestCheckMonitorById:
    """Integration-style tests for check_monitor_by_id.

    Uses the in-memory SQLite DB fixture + mocked httpx so no real network
    or PostgreSQL is involved.  The injected db_session parameter allows
    bypassing get_db_session() context manager entirely.
    """

    def _run_with_mock_response(
        self,
        db_session: Session,
        monitor: Monitor,
        status_code: int = 200,
    ) -> CheckResult | None:
        """Helper: run check_monitor_by_id with a mocked 'status_code' response."""
        with patch("app.modules.monitors.checker.httpx.Client") as mock_cls:
            ctx = mock_cls.return_value.__enter__.return_value
            ctx.request.return_value = _fake_response(status_code)
            return check_monitor_by_id(str(monitor.id), db_session=db_session)

    # AC-06.1 — healthy monitor → status=healthy, successes incremented
    def test_healthy_check_updates_success_counter(
        self, db_session: Session, base_monitor: Monitor
    ) -> None:
        result = self._run_with_mock_response(db_session, base_monitor, status_code=200)

        assert result is not None
        assert result.status == "healthy"
        db_session.refresh(base_monitor)
        assert base_monitor.consecutive_successes == 1
        assert base_monitor.consecutive_failures == 0

    # AC-06.2 — wrong status → status=failing, failures incremented
    def test_wrong_status_updates_failure_counter(
        self, db_session: Session, base_monitor: Monitor
    ) -> None:
        result = self._run_with_mock_response(db_session, base_monitor, status_code=503)

        assert result is not None
        assert result.status == "failing"
        db_session.refresh(base_monitor)
        assert base_monitor.consecutive_failures == 1
        assert base_monitor.consecutive_successes == 0

    # AC-06.3 — timeout → status=failing, timeout=True
    def test_timeout_failure_sets_timeout_flag(
        self, db_session: Session, base_monitor: Monitor
    ) -> None:
        with patch("app.modules.monitors.checker.httpx.Client") as mock_cls:
            ctx = mock_cls.return_value.__enter__.return_value
            ctx.request.side_effect = httpx.ReadTimeout("timed out", request=MagicMock())
            result = check_monitor_by_id(str(base_monitor.id), db_session=db_session)

        assert result is not None
        assert result.timeout is True
        assert result.status == "failing"
        db_session.refresh(base_monitor)
        assert base_monitor.consecutive_failures == 1

    # AC-06.4 — connection error → status=failing, connection_error=True
    def test_connection_error_sets_connection_error_flag(
        self, db_session: Session, base_monitor: Monitor
    ) -> None:
        with patch("app.modules.monitors.checker.httpx.Client") as mock_cls:
            ctx = mock_cls.return_value.__enter__.return_value
            ctx.request.side_effect = httpx.ConnectError("refused")
            result = check_monitor_by_id(str(base_monitor.id), db_session=db_session)

        assert result is not None
        assert result.connection_error is True
        assert result.status == "failing"

    # AC-06.5 — SSL error → status=failing, ssl_error=True
    def test_ssl_error_sets_ssl_error_flag(
        self, db_session: Session, base_monitor: Monitor
    ) -> None:
        with patch("app.modules.monitors.checker.httpx.Client") as mock_cls:
            ctx = mock_cls.return_value.__enter__.return_value
            ssl_exc = ssl.SSLError("cert verify failed")
            conn_exc = httpx.ConnectError("SSL error")
            conn_exc.__cause__ = ssl_exc
            ctx.request.side_effect = conn_exc
            result = check_monitor_by_id(str(base_monitor.id), db_session=db_session)

        assert result is not None
        assert result.ssl_error is True
        assert result.status == "failing"

    # AC-06.6 — one failure does not open incident (counter stays at 1)
    def test_single_failure_does_not_create_incident(
        self, db_session: Session, base_monitor: Monitor
    ) -> None:
        result = self._run_with_mock_response(db_session, base_monitor, status_code=500)

        db_session.refresh(base_monitor)
        # Only the counter is touched — no incident object exists
        assert base_monitor.consecutive_failures == 1
        assert result is not None
        assert result.status == "failing"

    # Counter reset after recovery: 3 failures → 1 success → failures reset
    def test_recovery_resets_failure_counter(
        self, db_session: Session, base_monitor: Monitor
    ) -> None:
        base_monitor.consecutive_failures = 3
        base_monitor.consecutive_successes = 0
        db_session.add(base_monitor)
        db_session.commit()

        result = self._run_with_mock_response(db_session, base_monitor, status_code=200)

        assert result is not None
        assert result.status == "healthy"
        db_session.refresh(base_monitor)
        assert base_monitor.consecutive_failures == 0
        assert base_monitor.consecutive_successes == 1

    # Skip soft-deleted monitor
    def test_skips_soft_deleted_monitor(
        self, db_session: Session, base_monitor: Monitor
    ) -> None:
        base_monitor.deleted_at = datetime.now(UTC)
        db_session.add(base_monitor)
        db_session.commit()

        result = check_monitor_by_id(str(base_monitor.id), db_session=db_session)
        assert result is None

    # Skip disabled monitor
    def test_skips_disabled_monitor(
        self, db_session: Session, base_monitor: Monitor
    ) -> None:
        base_monitor.enabled = False
        db_session.add(base_monitor)
        db_session.commit()

        result = check_monitor_by_id(str(base_monitor.id), db_session=db_session)
        assert result is None

    # Return None for unknown monitor ID
    def test_returns_none_for_unknown_monitor(self, db_session: Session) -> None:
        result = check_monitor_by_id(str(uuid4()), db_session=db_session)
        assert result is None

    # Result contains counter snapshots after the check
    def test_result_carries_counter_snapshot(
        self, db_session: Session, base_monitor: Monitor
    ) -> None:
        result = self._run_with_mock_response(db_session, base_monitor, status_code=200)

        assert result is not None
        assert result.consecutive_successes == 1
        assert result.consecutive_failures == 0

    # A malformed monitor id is skipped, not raised
    def test_returns_none_for_invalid_uuid(self, db_session: Session) -> None:
        result = check_monitor_by_id("not-a-uuid", db_session=db_session)
        assert result is None

    # A skipped (disabled) monitor keeps its counters untouched
    def test_skipped_monitor_leaves_counters_unchanged(
        self, db_session: Session, base_monitor: Monitor
    ) -> None:
        base_monitor.enabled = False
        base_monitor.consecutive_failures = 2
        db_session.add(base_monitor)
        db_session.commit()

        result = check_monitor_by_id(str(base_monitor.id), db_session=db_session)

        assert result is None
        db_session.refresh(base_monitor)
        assert base_monitor.consecutive_failures == 2
        assert base_monitor.consecutive_successes == 0

    # AC-06.6 — repeated failures accumulate and persist across checks
    def test_three_failures_accumulate_in_database(
        self, db_session: Session, base_monitor: Monitor
    ) -> None:
        for _ in range(3):
            self._run_with_mock_response(db_session, base_monitor, status_code=500)

        db_session.refresh(base_monitor)
        assert base_monitor.consecutive_failures == 3
        assert base_monitor.consecutive_successes == 0

    # Default User-Agent is used when the monitor has none
    def test_default_user_agent_used_when_monitor_has_none(
        self, db_session: Session, base_monitor: Monitor
    ) -> None:
        base_monitor.user_agent = None
        db_session.add(base_monitor)
        db_session.commit()

        with patch("app.modules.monitors.checker.httpx.Client") as mock_cls:
            ctx = mock_cls.return_value.__enter__.return_value
            ctx.request.return_value = _fake_response(200)
            check_monitor_by_id(str(base_monitor.id), db_session=db_session)

        sent_headers = ctx.request.call_args.kwargs["headers"]
        assert sent_headers["User-Agent"] == "APIMonitor/1.0"

        # Real-session path: no db_session injected, so get_db_session() is used
    def test_uses_get_db_session_when_none_injected(
        self, db_session: Session, base_monitor: Monitor
    ) -> None:
        with (
            patch("app.modules.monitors.checker.get_db_session") as mock_get,
            patch("app.modules.monitors.checker.httpx.Client") as mock_cls,
        ):
            mock_get.return_value.__enter__.return_value = db_session
            ctx = mock_cls.return_value.__enter__.return_value
            ctx.request.return_value = _fake_response(200)

            result = check_monitor_by_id(str(base_monitor.id))

        assert result is not None
        assert result.status == "healthy"
        mock_get.assert_called_once()
"""End-to-end integration test for US-10 (Task B4) and US-09 (Task B3).

Covers full lifecycle:
1. Endpoint is healthy.
2. Consecutive failures accumulate until failure_threshold is reached -> Opens incident.
3. Healthy check occurs -> Incident enters recovering state, recovery_count=1 (does not resolve).
4. Failure occurs -> Resets recovery progress (recovery_count=0), incident stays open.
5. Consecutive healthy checks reach recovery_threshold -> Incident resolves, counters reset.
6. Post-commit hook executes.
7. Subsequent failures cross failure_threshold -> A new distinct incident row opens.
"""

import socket
from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.modules.incidents.hooks import (
    clear_incident_resolved_hooks,
    register_incident_resolved_hook,
)
from app.modules.incidents.models import Incident, IncidentStatus
from app.modules.incidents.service import derive_incident_state
from app.modules.monitors.checker import check_monitor_by_id
from app.modules.monitors.models import Monitor


@pytest.fixture(autouse=True)
def _fake_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.modules.monitors.checker.socket.getaddrinfo",
        lambda *_args, **_kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))
        ],
    )


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()


@pytest.fixture(autouse=True)
def _cleanup_hooks() -> Generator[None, None, None]:
    clear_incident_resolved_hooks()
    yield
    clear_incident_resolved_hooks()


def _fake_http_response(status_code: int) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = ""
    return resp


def test_full_fail_open_recover_resolve_cycle(db_session: Session) -> None:
    """AC: State transitions and read endpoints have tests; an end-to-end test covers

    fail, open, recover, resolve.
    """
    mock_resolved_hook = MagicMock()
    register_incident_resolved_hook(mock_resolved_hook)

    # 1. Create a monitor with failure_threshold=3, recovery_threshold=2
    monitor = Monitor(
        id=uuid4(),
        team_id=uuid4(),
        name="Payment Gateway",
        url="https://api.example.com/health",
        method="GET",
        enabled=True,
        check_interval_seconds=60,
        current_interval_seconds=60,
        timeout_seconds=5,
        expected_status_code=200,
        failure_threshold=3,
        recovery_threshold=2,
        consecutive_failures=0,
        consecutive_successes=0,
        user_agent="APIMonitor/1.0",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(monitor)
    db_session.commit()

    with patch("app.modules.monitors.checker.httpx.Client") as mock_client_cls:
        client_instance = mock_client_cls.return_value.__enter__.return_value

        # --- STEP 1: Two initial failures (threshold is 3, no incident yet) ---
        client_instance.request.return_value = _fake_http_response(500)
        check_monitor_by_id(str(monitor.id), db_session=db_session)
        check_monitor_by_id(str(monitor.id), db_session=db_session)

        incidents = list(db_session.scalars(select(Incident)).all())
        assert len(incidents) == 0
        db_session.refresh(monitor)
        assert monitor.consecutive_failures == 2

        # --- STEP 2: Third failure hits threshold=3 -> OPEN INCIDENT ---
        check_monitor_by_id(str(monitor.id), db_session=db_session)

        incidents = list(db_session.scalars(select(Incident)).all())
        assert len(incidents) == 1
        first_incident = incidents[0]
        assert first_incident.status == IncidentStatus.OPEN
        assert first_incident.failure_count == 3
        assert first_incident.recovery_count == 0
        assert first_incident.resolved_at is None
        assert derive_incident_state(first_incident, monitor) == "failing"

        # --- STEP 3: First recovery check (200 OK) -> RECOVERING (1/2) ---
        client_instance.request.return_value = _fake_http_response(200)
        check_monitor_by_id(str(monitor.id), db_session=db_session)

        db_session.refresh(first_incident)
        db_session.refresh(monitor)
        assert first_incident.status == IncidentStatus.OPEN  # Still open!
        assert first_incident.recovery_count == 1
        assert derive_incident_state(first_incident, monitor) == "recovering"
        mock_resolved_hook.assert_not_called()

        # --- STEP 4: Failure during recovery -> RESETS RECOVERY PROGRESS ---
        client_instance.request.return_value = _fake_http_response(503)
        check_monitor_by_id(str(monitor.id), db_session=db_session)

        db_session.refresh(first_incident)
        db_session.refresh(monitor)
        assert first_incident.status == IncidentStatus.OPEN
        assert first_incident.recovery_count == 0  # Progress reset
        assert first_incident.failure_count == 4
        assert derive_incident_state(first_incident, monitor) == "failing"

        # --- STEP 5: First success of second recovery streak -> RECOVERING (1/2) ---
        client_instance.request.return_value = _fake_http_response(200)
        check_monitor_by_id(str(monitor.id), db_session=db_session)

        db_session.refresh(first_incident)
        assert first_incident.status == IncidentStatus.OPEN
        assert first_incident.recovery_count == 1

        # --- STEP 6: Second success reaches recovery_threshold=2 -> RESOLVED! ---
        check_monitor_by_id(str(monitor.id), db_session=db_session)

        db_session.refresh(first_incident)
        db_session.refresh(monitor)
        assert first_incident.status == IncidentStatus.RESOLVED
        assert first_incident.recovery_count == 2
        assert first_incident.resolved_at is not None
        assert derive_incident_state(first_incident, monitor) == "resolved"

        # Monitor counters are cleared
        assert monitor.consecutive_failures == 0
        assert monitor.consecutive_successes == 0

        # Post-commit hook has fired exactly once
        mock_resolved_hook.assert_called_once_with(first_incident.id)

        # --- STEP 7: New failure streak opens a new incident row ---
        client_instance.request.return_value = _fake_http_response(500)
        check_monitor_by_id(str(monitor.id), db_session=db_session)  # fail 1
        check_monitor_by_id(str(monitor.id), db_session=db_session)  # fail 2
        check_monitor_by_id(str(monitor.id), db_session=db_session)  # fail 3 (threshold)

        all_incidents = list(
            db_session.scalars(select(Incident).order_by(Incident.opened_at.asc())).all()
        )
        assert len(all_incidents) == 2
        assert all_incidents[0].id == first_incident.id
        assert all_incidents[0].status == IncidentStatus.RESOLVED

        second_incident = all_incidents[1]
        assert second_incident.id != first_incident.id
        assert second_incident.status == IncidentStatus.OPEN
        assert second_incident.failure_count == 3
        assert second_incident.recovery_count == 0

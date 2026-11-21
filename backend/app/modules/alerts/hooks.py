"""B5 alert hooks: register opened/resolved incident hooks to dispatch alerts.

Call ``register_b5_hooks()`` at application startup (main.py lifespan or celery_app).
"""

from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

logger = logging.getLogger(__name__)


def _opened_hook(
    incident_id: UUID,
    monitor_id: UUID,
    failure_count: int,
    opened_at: datetime,
) -> None:
    """Called after a new incident commits. Dispatches 'opened' alert deliveries."""
    from app.db.session import get_db_session
    from app.modules.alerts.dispatcher import dispatch_alert
    from app.modules.monitors.models import Monitor

    try:
        with get_db_session() as session:
            monitor = session.get(Monitor, monitor_id)
            if monitor is None:
                logger.warning(
                    "_opened_hook: monitor %s not found for incident %s", monitor_id, incident_id
                )
                return
            dispatch_alert(
                session=session,
                incident_id=incident_id,
                monitor_id=monitor_id,
                team_id=monitor.team_id,
                event_type="opened",
            )
    except Exception:
        logger.exception("_opened_hook: error dispatching alert for incident %s", incident_id)


def _resolved_hook(incident_id: UUID) -> None:
    """Called after an incident resolves. Dispatches 'resolved' alert deliveries."""
    from app.db.session import get_db_session
    from app.modules.alerts.dispatcher import dispatch_alert
    from app.modules.incidents.models import Incident
    from app.modules.monitors.models import Monitor

    try:
        with get_db_session() as session:
            incident = session.get(Incident, incident_id)
            if incident is None:
                logger.warning("_resolved_hook: incident %s not found", incident_id)
                return
            monitor = session.get(Monitor, incident.monitor_id)
            if monitor is None:
                logger.warning(
                    "_resolved_hook: monitor %s not found for incident %s",
                    incident.monitor_id,
                    incident_id,
                )
                return
            dispatch_alert(
                session=session,
                incident_id=incident_id,
                monitor_id=monitor.id,
                team_id=monitor.team_id,
                event_type="resolved",
            )
    except Exception:
        logger.exception("_resolved_hook: error dispatching alert for incident %s", incident_id)


def register_b5_hooks() -> None:
    """Register B5 alert hooks for both incident opened and incident resolved events."""
    from app.modules.incidents.hooks import register_incident_resolved_hook
    from app.modules.incidents.models import register_incident_opened_hook

    register_incident_opened_hook(_opened_hook)
    register_incident_resolved_hook(_resolved_hook)
    logger.info("B5 alert hooks registered.")


def unregister_b5_hooks() -> None:
    """Remove B5 alert hooks (used in test teardown)."""
    from app.modules.incidents.hooks import unregister_incident_resolved_hook
    from app.modules.incidents.models import unregister_incident_opened_hook

    unregister_incident_opened_hook(_opened_hook)
    unregister_incident_resolved_hook(_resolved_hook)

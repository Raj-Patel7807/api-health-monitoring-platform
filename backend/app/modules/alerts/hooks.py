"""B5 alert hooks: register opened/resolved incident hooks to dispatch alerts.

Call ``register_b5_hooks()`` at application startup (main.py lifespan or celery_app).
"""

from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

logger = logging.getLogger(__name__)


def _publish(incident_id: UUID, event_type: str) -> None:
    from app.db.session import get_db_session
    from app.modules.alerts.dispatcher import publish_pending_deliveries
    from app.modules.alerts.models import AlertDelivery

    with get_db_session() as session:
        publish_pending_deliveries(
            session,
            AlertDelivery.incident_id == incident_id,
            AlertDelivery.event_type == event_type,
        )


def _opened_hook(
    incident_id: UUID, monitor_id: UUID, failure_count: int, opened_at: datetime
) -> None:
    _publish(incident_id, "opened")
    try:
        from app.workers.tasks import analyze_incident

        analyze_incident.delay(str(incident_id))
    except Exception as exc:
        logger.debug("Asynchronous AI analysis dispatch skipped or deferred: %s", exc)


def _resolved_hook(incident_id: UUID) -> None:
    _publish(incident_id, "resolved")


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

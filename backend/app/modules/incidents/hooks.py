"""Post-commit hook dispatch for resolved incidents (US-10 / B5 integration).

Ensures that alert dispatch and external notification hooks for B5 fire:
1. Only after the database transaction has committed successfully.
2. Exactly once per resolved incident.
"""

import logging
from collections.abc import Callable
from uuid import UUID

from sqlalchemy import event
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

IncidentResolvedHook = Callable[[UUID], None]

_RESOLVED_HOOKS: list[IncidentResolvedHook] = []


def register_incident_resolved_hook(hook: IncidentResolvedHook) -> None:
    """Register a callback for B5 alert dispatch when an incident is resolved."""
    if hook not in _RESOLVED_HOOKS:
        _RESOLVED_HOOKS.append(hook)


def unregister_incident_resolved_hook(hook: IncidentResolvedHook) -> None:
    """Remove a previously registered hook callback."""
    if hook in _RESOLVED_HOOKS:
        _RESOLVED_HOOKS.remove(hook)


def get_incident_resolved_hooks() -> list[IncidentResolvedHook]:
    """Return a copy of the registered incident-resolved hooks."""
    return list(_RESOLVED_HOOKS)


def clear_incident_resolved_hooks() -> None:
    """Clear all registered hooks (primarily used for test cleanup)."""
    _RESOLVED_HOOKS.clear()


def schedule_incident_resolved_hook(session: Session, incident_id: UUID) -> None:
    """Schedule the resolved hook to execute strictly after session.commit().

    Uses session.info to track pending resolved incident IDs and session-level event
    listeners to ensure hooks never fire during rollbacks or prior to commit completion.
    """
    pending: set[UUID] = session.info.setdefault("pending_resolved_incident_ids", set())
    pending.add(incident_id)

    if session.info.get("resolved_hook_listener_attached"):
        return

    session.info["resolved_hook_listener_attached"] = True

    def _on_after_commit(sess: Session) -> None:
        pending_set = sess.info.get("pending_resolved_incident_ids")
        if not pending_set:
            return
        incident_ids = list(pending_set)
        sess.info["pending_resolved_incident_ids"] = set()

        for inc_id in incident_ids:
            for hook in list(_RESOLVED_HOOKS):
                try:
                    hook(inc_id)
                except Exception:
                    logger.exception(
                        "Error executing incident resolved hook for incident %s", inc_id
                    )

    def _on_after_rollback(sess: Session) -> None:
        sess.info["pending_resolved_incident_ids"] = set()

    event.listen(session, "after_commit", _on_after_commit)
    event.listen(session, "after_rollback", _on_after_rollback)

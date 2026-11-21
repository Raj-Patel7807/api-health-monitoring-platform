"""Incidents module (US-09 / US-10)."""

from app.modules.incidents.hooks import (
    IncidentResolvedHook,
    clear_incident_resolved_hooks,
    get_incident_resolved_hooks,
    register_incident_resolved_hook,
    schedule_incident_resolved_hook,
    unregister_incident_resolved_hook,
)
from app.modules.incidents.models import (
    Incident,
    IncidentHook,
    IncidentStatus,
    get_incident_opened_hooks,
    register_incident_opened_hook,
    unregister_incident_opened_hook,
)

__all__ = [
    "Incident",
    "IncidentStatus",
    "IncidentHook",
    "register_incident_opened_hook",
    "unregister_incident_opened_hook",
    "get_incident_opened_hooks",
    "IncidentResolvedHook",
    "register_incident_resolved_hook",
    "unregister_incident_resolved_hook",
    "get_incident_resolved_hooks",
    "clear_incident_resolved_hooks",
    "schedule_incident_resolved_hook",
]

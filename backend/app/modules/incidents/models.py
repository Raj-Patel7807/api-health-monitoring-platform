import enum
from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Enum, ForeignKey, Index, Integer, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, DateTimeUTC

if TYPE_CHECKING:
    from app.modules.monitors.models import Monitor

# Type alias for incident-opened callback hooks
IncidentHook = Callable[[UUID, UUID, int, datetime], None]

# Global registry of incident-opened hooks (e.g. for B5 alerts in future)
_INCIDENT_OPENED_HOOKS: list[IncidentHook] = []


def register_incident_opened_hook(hook: IncidentHook) -> None:
    """Register a callback to be executed after a newly opened incident commits.

    Hook signature:
    (incident_id: UUID, monitor_id: UUID, failure_count: int, opened_at: datetime) -> None
    """
    if hook not in _INCIDENT_OPENED_HOOKS:
        _INCIDENT_OPENED_HOOKS.append(hook)


def unregister_incident_opened_hook(hook: IncidentHook) -> None:
    """Remove a previously registered incident-opened callback hook."""
    if hook in _INCIDENT_OPENED_HOOKS:
        _INCIDENT_OPENED_HOOKS.remove(hook)


def get_incident_opened_hooks() -> list[IncidentHook]:
    """Return a copy of the registered incident-opened hooks."""
    return list(_INCIDENT_OPENED_HOOKS)


class IncidentStatus(enum.StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"


class Incident(Base):
    """SQLAlchemy model for the incidents table."""

    __tablename__ = "incidents"
    __table_args__ = (
        Index(
            "ux_incident_one_open_per_monitor",
            "monitor_id",
            unique=True,
            postgresql_where=text("status = 'open'"),
            sqlite_where=text("status = 'open'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    monitor_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("monitors.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        Enum("open", "resolved", name="incident_status", create_type=False),
        default="open",
        nullable=False,
    )
    opened_at: Mapped[datetime] = mapped_column(
        DateTimeUTC,
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTimeUTC, nullable=True)
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    recovery_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    monitor: Mapped["Monitor"] = relationship("Monitor")

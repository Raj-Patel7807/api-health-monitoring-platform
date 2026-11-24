"""SQLAlchemy ORM model for ai_analyses table."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, DateTimeUTC


class AIAnalysis(Base):
    """Advisory AI analysis and diagnosis for an incident.

    NOTE: Monitoring and incident status remain strictly deterministic.
    AI analysis is purely an explanatory and advisory artifact.
    """

    __tablename__ = "ai_analyses"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    incident_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    status: Mapped[str] = mapped_column(String(50), default="completed", nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_actions: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    investigation_steps: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    prevention_steps: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    model: Mapped[str] = mapped_column(String(100), default="deterministic-rules", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTimeUTC, nullable=False, server_default=func.now()
    )

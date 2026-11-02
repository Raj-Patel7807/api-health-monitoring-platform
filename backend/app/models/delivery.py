from sqlalchemy import Column, String, Integer, DateTime, Enum, JSON, func
from sqlalchemy.dialects.postgresql import UUID
import enum
import uuid
from app.db.session import Base


class ChannelType(str, enum.Enum):
    email = "email"
    webhook = "webhook"


class DeliveryStatus(str, enum.Enum):
    success = "success"
    failed = "failed"
    retrying = "retrying"
    dead_letter = "dead_letter"


class DeliveryLog(Base):
    __tablename__ = "delivery_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False)
    channel_type = Column(Enum(ChannelType), nullable=False)
    event_type = Column(String, nullable=False)
    recipient = Column(String, nullable=False)
    request_payload = Column(JSON, nullable=False)
    response_status_code = Column(Integer, nullable=True)
    response_body = Column(String, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    attempt_count = Column(Integer, default=1)
    max_attempts = Column(Integer, default=5)
    status = Column(Enum(DeliveryStatus), default=DeliveryStatus.retrying)
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def update_status(self, new_status: DeliveryStatus, error: str | None = None):
        self.status = new_status
        if error:
            self.error_message = error

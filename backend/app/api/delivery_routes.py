from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid

from app.db.session import create_database_engine
from app.models.delivery import DeliveryLog, DeliveryStatus, ChannelType
from app.core.config import get_settings

router = APIRouter(prefix="/deliveries", tags=["deliveries"])

SessionLocal = Session(bind=create_database_engine())


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/", response_model=List[dict])
def list_deliveries(
    status: Optional[DeliveryStatus] = Query(None),
    channel: Optional[ChannelType] = Query(None),
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    query = db.query(DeliveryLog)
    if status:
        query = query.filter(DeliveryLog.status == status)
    if channel:
        query = query.filter(DeliveryLog.channel_type == channel)
    deliveries = query.offset(offset).limit(limit).all()
    return [
        {
            "id": str(d.id),
            "channel_type": d.channel_type.value,
            "event_type": d.event_type,
            "recipient": d.recipient,
            "status": d.status.value,
            "attempt_count": d.attempt_count,
            "created_at": d.created_at,
        }
        for d in deliveries
    ]


@router.get("/{delivery_id}", response_model=dict)
def get_delivery(delivery_id: str, db: Session = Depends(get_db)):
    delivery = db.query(DeliveryLog).filter(DeliveryLog.id == uuid.UUID(delivery_id)).first()
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")
    return {
        "id": str(delivery.id),
        "channel_type": delivery.channel_type.value,
        "event_type": delivery.event_type,
        "recipient": delivery.recipient,
        "status": delivery.status.value,
        "attempt_count": delivery.attempt_count,
        "request_payload": delivery.request_payload,
        "response_status_code": delivery.response_status_code,
        "response_body": delivery.response_body,
        "latency_ms": delivery.latency_ms,
        "error_message": delivery.error_message,
        "created_at": delivery.created_at,
        "updated_at": delivery.updated_at,
    }


@router.post("/{delivery_id}/replay", response_model=dict)
def replay_delivery(delivery_id: str, db: Session = Depends(get_db)):
    delivery = db.query(DeliveryLog).filter(DeliveryLog.id == uuid.UUID(delivery_id)).first()
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")
    # Reset attempt count and status, then enqueue Celery task
    delivery.attempt_count = 0
    delivery.status = DeliveryStatus.retrying
    db.commit()
    from app.workers.tasks import replay_delivery_task

    replay_delivery_task.delay(str(delivery.id))
    return {"message": "Replay enqueued", "delivery_id": delivery_id}

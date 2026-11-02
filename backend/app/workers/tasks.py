from app.workers.celery_app import celery_app
from app.db.session import create_database_engine
from sqlalchemy.orm import sessionmaker
from app.services.email_sender import send_email
from app.services.webhook_sender import send_webhook
from app.models.delivery import DeliveryLog, DeliveryStatus
import uuid


@celery_app.task(name="app.workers.tasks.run_health_check")
def run_health_check(monitor_id: str) -> str:
    """Reserve the monitoring queue contract; monitor logic is a later feature."""

    return monitor_id


@celery_app.task(name="app.workers.tasks.dispatch_notification")
def dispatch_notification(delivery_id: str) -> str:
    """Reserve notification delivery work without contacting a provider yet."""

    return delivery_id


@celery_app.task(name="app.workers.tasks.analyze_incident")
def analyze_incident(incident_id: str) -> str:
    """Reserve advisory AI work; it must not determine monitoring facts."""

    return incident_id

@celery_app.task(name="app.workers.tasks.send_email_task")
def send_email_task(delivery_id: str) -> str:
    """Celery task to send an email based on a DeliveryLog record."""
    db_engine = create_database_engine()
    SessionLocal = sessionmaker(bind=db_engine)
    db = SessionLocal()
    delivery = db.query(DeliveryLog).filter(DeliveryLog.id == uuid.UUID(delivery_id)).first()
    if not delivery:
        raise ValueError(f"Delivery {delivery_id} not found")
    # Assume delivery.request_payload contains keys: to, subject, template_data
    payload = delivery.request_payload
    result = send_email(to=payload["to"], subject=payload["subject"], template_data=payload.get("template_data", {}))
    # Update delivery status based on result
    if result:
        delivery.update_status(DeliveryStatus.success)
    else:
        delivery.update_status(DeliveryStatus.failed)
    db.commit()
    db.close()
    return delivery_id

@celery_app.task(name="app.workers.tasks.send_webhook_task")
def send_webhook_task(delivery_id: str) -> str:
    """Celery task to send a webhook based on a DeliveryLog record."""
    db_engine = create_database_engine()
    SessionLocal = sessionmaker(bind=db_engine)
    db = SessionLocal()
    delivery = db.query(DeliveryLog).filter(DeliveryLog.id == uuid.UUID(delivery_id)).first()
    if not delivery:
        raise ValueError(f"Delivery {delivery_id} not found")
    payload = delivery.request_payload
    url = payload.get("url")
    event_type = payload.get("event_type", "unknown")
    body = payload.get("payload", {})
    result_id = send_webhook(url=url, payload={"event_type": event_type, **body})
    # Update status based on send_webhook return – it logs itself
    delivery.update_status(DeliveryStatus.success)
    db.commit()
    db.close()
    return delivery_id

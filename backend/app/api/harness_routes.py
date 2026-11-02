from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import uuid

from app.workers.tasks import send_email_task, send_webhook_task

router = APIRouter(prefix="/harness", tags=["harness"])


class EmailPayload(BaseModel):
    to: str
    subject: str
    template_data: dict


class WebhookPayload(BaseModel):
    url: str
    event_type: str
    payload: dict


@router.post("/email")
def trigger_email(payload: EmailPayload):
    task_id = send_email_task.delay(payload.dict())
    return {"message": "Email task queued", "task_id": task_id}


@router.post("/webhook")
def trigger_webhook(payload: WebhookPayload):
    task_id = send_webhook_task.delay(payload.dict())
    return {"message": "Webhook task queued", "task_id": task_id}

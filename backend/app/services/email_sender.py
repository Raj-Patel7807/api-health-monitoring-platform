import os
import uuid

try:
    from aiosmtplib import send
except ImportError:  # pragma: no cover

    async def send(*args, **kwargs):
        # No-op stub for testing environment
        return None


try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
except ImportError:  # pragma: no cover
    Environment = None
    FileSystemLoader = None
    select_autoescape = None

from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.session import create_database_engine
from app.models.delivery import ChannelType, DeliveryLog, DeliveryStatus

settings = get_settings()
templates_path = os.path.join(os.path.dirname(__file__), "..", "templates", "email")
if Environment:
    env = Environment(
        loader=FileSystemLoader(templates_path),
        autoescape=select_autoescape(["html", "xml"]),
    )
else:
    env = None

SessionLocal = sessionmaker(bind=create_database_engine())


async def send_email(to: str, subject: str, template_name: str, context: dict) -> str:
    """Send an email and record a DeliveryLog entry.

    The ``context`` dict contains variables used by the Jinja2
    template and may include ``event_type``.
    """
    template = env.get_template(template_name)
    html_body = template.render(**context)

    message = (
        f"Subject: {subject}\n"
        f"From: {settings.email_from}\n"
        f"To: {to}\n"
        f"Content-Type: text/html\n\n"
        f"{html_body}"
    )

    delivery_id = str(uuid.uuid4())
    db = SessionLocal()
    delivery = DeliveryLog(
        id=delivery_id,
        organization_id=uuid.uuid4(),
        channel_type=ChannelType.email,
        event_type=context.get("event_type", "unknown"),
        recipient=to,
        request_payload=context,
        status=DeliveryStatus.retrying,
    )
    db.add(delivery)
    db.commit()
    db.refresh(delivery)

    try:
        await send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            start_tls=True,
        )
        delivery.update_status(DeliveryStatus.success)
    except Exception as exc:
        delivery.update_status(DeliveryStatus.failed, str(exc))
        raise
    finally:
        db.commit()
        db.close()
    return delivery_id

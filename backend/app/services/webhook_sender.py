from __future__ import annotations

import hashlib
import hmac
import json
import os
import uuid
from typing import Any
from urllib.parse import urlparse

import httpx
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.session import create_database_engine
from app.models.delivery import ChannelType, DeliveryLog, DeliveryStatus

settings = get_settings()
SessionLocal = sessionmaker(bind=create_database_engine())


def _is_private_ip(host: str) -> bool:
    # Simple check for private ranges
    private_prefixes = (
        "10.",
        "172.16.",
        "172.17.",
        "172.18.",
        "172.19.",
        "172.20.",
        "172.21.",
        "172.22.",
        "172.23.",
        "172.24.",
        "172.25.",
        "172.26.",
        "172.27.",
        "172.28.",
        "172.29.",
        "172.30.",
        "172.31.",
        "192.168.",
        "127.",
        "169.254.",
    )
    return host.startswith(private_prefixes)


async def send_webhook(
    url: str, payload: dict[str, Any], headers: dict[str, str] | None = None
) -> str:
    """Send a webhook with HMAC signing, SSRF guard and retry logic.
    Returns the delivery_id stored in the DB.
    """
    parsed = urlparse(url)
    if _is_private_ip(parsed.hostname or ""):
        raise ValueError("Attempted to send webhook to a private IP address")

    delivery_id = str(uuid.uuid4())
    db = SessionLocal()
    delivery = DeliveryLog(
        id=delivery_id,
        organization_id=uuid.uuid4(),
        channel_type=ChannelType.webhook,
        event_type=payload.get("event_type", "unknown"),
        recipient=url,
        request_payload=payload,
        status=DeliveryStatus.retrying,
    )
    db.add(delivery)
    db.commit()
    db.refresh(delivery)

    # Prepare HMAC signature
    secret = settings.webhook_secret.encode()
    body = json.dumps(payload).encode()
    signature = hmac.new(secret, body, hashlib.sha256).hexdigest()
    default_headers: dict[str, str] = {
        "Content-Type": "application/json",
        "X-Monitoring-Signature": signature,
    }
    if headers:
        default_headers.update(headers)

    max_attempts: int = int(delivery.max_attempts or 5)
    attempt = 0
    while attempt < max_attempts:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url, content=body, headers=default_headers, timeout=10.0
                )
            delivery.response_status_code = response.status_code  # type: ignore[assignment]
            delivery.response_body = response.text  # type: ignore[assignment]
            if 200 <= response.status_code < 300:
                delivery.update_status(DeliveryStatus.success)
                break
            else:
                raise httpx.HTTPStatusError(
                    "Non-2xx response", request=response.request, response=response
                )
        except Exception as exc:
            attempt += 1
            delivery.attempt_count = attempt  # type: ignore[assignment]
            if attempt >= max_attempts:
                delivery.update_status(DeliveryStatus.dead_letter, str(exc))
                break
            delivery.update_status(DeliveryStatus.retrying, str(exc))
            # exponential backoff with jitter
            backoff = (2**attempt) + (os.urandom(1)[0] % 1000) / 1000
            await httpx.AsyncClient().get("http://localhost", timeout=backoff)  # cheap sleep
    db.commit()
    db.close()
    return delivery_id

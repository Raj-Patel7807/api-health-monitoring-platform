"""HTTPS transport for incident webhooks."""

import hashlib
import hmac
import json
from typing import Any

import httpx

from app.core.config import get_settings
from app.modules.monitors.checker import is_public_target


def send_webhook(url: str, payload: dict[str, Any]) -> None:
    if not url.startswith("https://") or not is_public_target(url):
        raise ValueError("Invalid webhook destination")
    body = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"}
    secret = get_settings().webhook_secret
    if secret:
        headers["X-Monitoring-Signature"] = hmac.new(
            secret.encode(), body, hashlib.sha256
        ).hexdigest()
    with httpx.Client(timeout=5.0, trust_env=False) as client:
        with client.stream("POST", url, content=body, headers=headers) as response:
            response.raise_for_status()

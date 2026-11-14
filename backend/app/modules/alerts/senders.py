"""Alert senders for US-11 (B5): common interface, Slack, Discord.

Security rules (enforced here):
- The secret is decrypted ONLY inside the send function (never before, never stored).
- Secrets and URLs are never logged or stored in error_message.
- A 5-second httpx timeout is used for all outbound calls.
"""

from __future__ import annotations

import abc
import logging
import re
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


class AlertSendError(Exception):
    """Raised when an alert delivery fails. Message must be sanitized (no URL/token)."""


def _sanitize_error(msg: str, secret: str) -> str:
    """Remove the secret/URL from an error message so it is safe to store."""
    if not secret:
        return msg
    # Remove the secret itself
    sanitized = msg.replace(secret, "[REDACTED]")
    # Also strip any https:// URLs generically to avoid leaking webhook URLs
    sanitized = re.sub(r"https?://\S+", "[REDACTED_URL]", sanitized)
    return sanitized


def _format_message(
    monitor_name: str,
    monitor_url: str,
    event_type: str,
    checked_at: datetime,
    failure_reason: str | None,
) -> str:
    """Format the alert text shared by all senders."""
    tag = "[OPENED]" if event_type == "opened" else "[RESOLVED]"
    ts = checked_at.strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"{tag} {monitor_name} ({monitor_url}) \u2014 {ts}"
    if event_type == "opened" and failure_reason:
        line += f"\nReason: {failure_reason}"
    return line


@dataclass
class AlertMessage:
    """Payload passed to every sender."""

    monitor_name: str
    monitor_url: str
    event_type: str  # "opened" | "resolved"
    checked_at: datetime
    failure_reason: str | None = None


class AlertSender(abc.ABC):
    """Abstract base for all alert channel senders."""

    @abc.abstractmethod
    def send(self, channel: object, message: AlertMessage) -> None:
        """Send the alert message to the channel.

        Args:
            channel: A NotificationChannel ORM instance.
            message: The structured alert payload.

        Raises:
            AlertSendError: If delivery fails. Message is guaranteed sanitized.
        """


class SlackSender(AlertSender):
    """Posts to a Slack incoming webhook URL stored (encrypted) in channel.secret_ref."""

    def send(self, channel: object, message: AlertMessage) -> None:  # type: ignore[override]
        import httpx

        from app.core.crypto import decrypt

        # Decrypt secret in memory only — never assign to a module-level var
        webhook_url: str = decrypt(channel.secret_ref)  # type: ignore[attr-defined]
        text = _format_message(
            monitor_name=message.monitor_name,
            monitor_url=message.monitor_url,
            event_type=message.event_type,
            checked_at=message.checked_at,
            failure_reason=message.failure_reason,
        )
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.post(webhook_url, json={"text": text})
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            safe_msg = _sanitize_error(
                f"Slack webhook returned HTTP {exc.response.status_code}", webhook_url
            )
            raise AlertSendError(safe_msg) from None
        except httpx.RequestError as exc:
            safe_msg = _sanitize_error(
                f"Slack webhook request error: {type(exc).__name__}", webhook_url
            )
            raise AlertSendError(safe_msg) from None
        finally:
            # Explicitly clear webhook_url from local scope (best-effort in Python)
            webhook_url = ""  # noqa: F841  # type: ignore[assignment]


class DiscordSender(AlertSender):
    """Posts to a Discord webhook URL stored (encrypted) in channel.secret_ref."""

    def send(self, channel: object, message: AlertMessage) -> None:  # type: ignore[override]
        import httpx

        from app.core.crypto import decrypt

        webhook_url: str = decrypt(channel.secret_ref)  # type: ignore[attr-defined]
        text = _format_message(
            monitor_name=message.monitor_name,
            monitor_url=message.monitor_url,
            event_type=message.event_type,
            checked_at=message.checked_at,
            failure_reason=message.failure_reason,
        )
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.post(webhook_url, json={"content": text})
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            safe_msg = _sanitize_error(
                f"Discord webhook returned HTTP {exc.response.status_code}", webhook_url
            )
            raise AlertSendError(safe_msg) from None
        except httpx.RequestError as exc:
            safe_msg = _sanitize_error(
                f"Discord webhook request error: {type(exc).__name__}", webhook_url
            )
            raise AlertSendError(safe_msg) from None
        finally:
            webhook_url = ""  # noqa: F841  # type: ignore[assignment]


def get_sender(channel_type: str) -> AlertSender:
    """Factory: return the appropriate AlertSender for the given channel type.

    Args:
        channel_type: One of "slack", "discord".

    Raises:
        ValueError: For unsupported channel types.
    """
    _registry: dict[str, AlertSender] = {
        "slack": SlackSender(),
        "discord": DiscordSender(),
    }
    sender = _registry.get(channel_type)
    if sender is None:
        raise ValueError(f"Unsupported alert channel type: {channel_type!r}")
    return sender

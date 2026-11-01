"""Pydantic schemas for notification channel CRUD and validation (US-03).

Secret validation rules per API.md:
  slack   — must start with https://hooks.slack.com/
  discord — must start with https://discord.com/api/webhooks/
  webhook — https:// only; localhost and private IP ranges rejected (SSRF guard)
  email   — valid email address

The raw secret is write-only and is never returned in any response.
"""

import re
from datetime import datetime
from ipaddress import AddressValueError, IPv4Address, IPv6Address
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError

from app.modules.channels.models import ChannelType

# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

# RFC 1918 / loopback private ranges for SSRF guard (webhook type).
_PRIVATE_PREFIXES = (
    "10.",
    "192.168.",
    "127.",
    "0.",
    "169.254.",
    "::1",
    "fc",
    "fd",
)


def _is_private_host(host: str) -> bool:
    """Return True for localhost, loopback, and RFC-1918 addresses."""
    lower = host.lower().split(":")[0]  # strip port if present
    if lower in ("localhost", "::1"):
        return True
    for pfx in _PRIVATE_PREFIXES:
        if lower.startswith(pfx):
            return True
    # Numeric IP check
    try:
        addr = IPv4Address(lower)
        return addr.is_private or addr.is_loopback or addr.is_link_local
    except AddressValueError:
        pass
    try:
        addr6 = IPv6Address(lower)
        return addr6.is_private or addr6.is_loopback or addr6.is_link_local
    except AddressValueError:
        pass
    return False


def _validate_secret(channel_type: ChannelType, secret: str) -> str:
    """Validate secret_value according to channel type rules from API.md."""
    s = secret.strip()
    if not s:
        raise PydanticCustomError("value_error", "Secret value cannot be empty.")

    if channel_type == ChannelType.slack:
        if not s.startswith("https://hooks.slack.com/"):
            raise PydanticCustomError(
                "value_error",
                "Slack webhook URL must start with https://hooks.slack.com/",
            )

    elif channel_type == ChannelType.discord:
        if not s.startswith("https://discord.com/api/webhooks/"):
            raise PydanticCustomError(
                "value_error",
                "Discord webhook URL must start with https://discord.com/api/webhooks/",
            )

    elif channel_type == ChannelType.webhook:
        parsed = urlparse(s)
        if parsed.scheme != "https":
            raise PydanticCustomError(
                "value_error",
                "Webhook URL must use https://",
            )
        if not parsed.netloc:
            raise PydanticCustomError("value_error", "Webhook URL must have a valid host.")
        host = parsed.hostname or ""
        if _is_private_host(host):
            # SSRF guard: reject private / loopback targets.
            raise PydanticCustomError(
                "value_error",
                "Webhook URL must not target localhost or private IP ranges.",
            )

    elif channel_type == ChannelType.email:
        if not _EMAIL_RE.match(s):
            raise PydanticCustomError("value_error", "Must be a valid email address.")

    return s


def _make_display_hint(channel_type: ChannelType, secret: str) -> str:
    """Build a safe, non-secret preview of the secret for UI display.

    The result is stored in secret_display_hint and shown to users; it must
    never allow reconstruction of the full secret.
    """
    s = secret.strip()

    if channel_type in (ChannelType.slack, ChannelType.discord, ChannelType.webhook):
        # Show host + first few path chars + "…" + last 3 chars of path
        parsed = urlparse(s)
        path = parsed.path or ""
        suffix = path[-3:] if len(path) >= 3 else path
        return f"{parsed.netloc}/…/{suffix}"

    elif channel_type == ChannelType.email:
        # Show only first char + domain: "r…@example.com"
        local, _, domain = s.partition("@")
        return f"{local[0]}…@{domain}" if local else f"…@{domain}"

    return "…"


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class ChannelCreateRequest(BaseModel):
    type: ChannelType
    name: str = Field(..., min_length=1, max_length=150)
    monitor_id: UUID | None = None
    # Write-only; validated against type then discarded after hint is built.
    secret_value: str = Field(..., min_length=1)
    configuration: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise PydanticCustomError("value_error", "Name cannot be empty or whitespace only.")
        return cleaned

    @model_validator(mode="after")
    def validate_secret_against_type(self) -> "ChannelCreateRequest":
        self.secret_value = _validate_secret(self.type, self.secret_value)
        return self


class ChannelUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    is_enabled: bool | None = None
    # Omit to keep the current secret; provide to rotate it.
    secret_value: str | None = Field(default=None, min_length=1)
    configuration: dict[str, Any] | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        if v is not None:
            cleaned = v.strip()
            if not cleaned:
                raise PydanticCustomError("value_error", "Name cannot be empty or whitespace only.")
            return cleaned
        return v


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class ChannelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: str
    name: str
    monitor_id: UUID | None
    is_enabled: bool
    secret_display_hint: str | None
    configuration: Any
    created_at: datetime
    updated_at: datetime


class ChannelListResponse(BaseModel):
    items: list[ChannelResponse]

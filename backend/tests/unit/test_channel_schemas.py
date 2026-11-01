"""Unit tests for notification channel Pydantic schemas (US-03).

Covers:
- Secret validation per channel type (happy path and error cases)
- SSRF guard for webhook type
- display hint generation
- Field validation (name length, required fields)
- ChannelUpdateRequest (partial fields, type/monitor_id immutability is at router level)
"""

import pytest
from pydantic import ValidationError
from pydantic_core import PydanticCustomError

from app.modules.channels.models import ChannelType
from app.modules.channels.schemas import (
    ChannelCreateRequest,
    ChannelUpdateRequest,
    _make_display_hint,
    _validate_secret,
)

# ---------------------------------------------------------------------------
# _validate_secret — per-type rules
# ---------------------------------------------------------------------------


class TestValidateSecretSlack:
    def test_valid_slack_url(self) -> None:
        result = _validate_secret(
            ChannelType.slack,
            "https://hooks.slack.com/services/T00/B00/XXXX",
        )
        assert result == "https://hooks.slack.com/services/T00/B00/XXXX"

    def test_rejects_wrong_prefix(self) -> None:
        with pytest.raises(PydanticCustomError, match="hooks.slack.com"):
            _validate_secret(ChannelType.slack, "https://example.com/webhook")

    def test_rejects_empty(self) -> None:
        with pytest.raises(PydanticCustomError):
            _validate_secret(ChannelType.slack, "   ")


class TestValidateSecretDiscord:
    def test_valid_discord_url(self) -> None:
        result = _validate_secret(
            ChannelType.discord,
            "https://discord.com/api/webhooks/123/abc",
        )
        assert result.startswith("https://discord.com/api/webhooks/")

    def test_rejects_wrong_host(self) -> None:
        with pytest.raises(PydanticCustomError, match="discord.com/api/webhooks/"):
            _validate_secret(ChannelType.discord, "https://discord.gg/123")


class TestValidateSecretWebhook:
    def test_valid_public_https(self) -> None:
        result = _validate_secret(
            ChannelType.webhook,
            "https://my-service.example.com/hook",
        )
        assert result.startswith("https://")

    def test_rejects_http(self) -> None:
        with pytest.raises(PydanticCustomError, match="https://"):
            _validate_secret(ChannelType.webhook, "http://my-service.example.com/hook")

    def test_rejects_localhost(self) -> None:
        with pytest.raises(PydanticCustomError, match="private"):
            _validate_secret(ChannelType.webhook, "https://localhost/hook")

    def test_rejects_127_0_0_1(self) -> None:
        with pytest.raises(PydanticCustomError, match="private"):
            _validate_secret(ChannelType.webhook, "https://127.0.0.1/hook")

    def test_rejects_private_rfc1918(self) -> None:
        with pytest.raises(PydanticCustomError, match="private"):
            _validate_secret(ChannelType.webhook, "https://192.168.1.1/hook")

    def test_rejects_10_dot_prefix(self) -> None:
        with pytest.raises(PydanticCustomError, match="private"):
            _validate_secret(ChannelType.webhook, "https://10.0.0.1/hook")


class TestValidateSecretEmail:
    def test_valid_email(self) -> None:
        result = _validate_secret(ChannelType.email, "alerts@example.com")
        assert result == "alerts@example.com"

    def test_strips_whitespace(self) -> None:
        result = _validate_secret(ChannelType.email, "  user@test.org  ")
        assert result == "user@test.org"

    def test_rejects_invalid_email(self) -> None:
        with pytest.raises(PydanticCustomError, match="valid email"):
            _validate_secret(ChannelType.email, "not-an-email")

    def test_rejects_no_at(self) -> None:
        with pytest.raises(PydanticCustomError, match="valid email"):
            _validate_secret(ChannelType.email, "nodomain")


# ---------------------------------------------------------------------------
# _make_display_hint
# ---------------------------------------------------------------------------


class TestMakeDisplayHint:
    def test_slack_hint_has_host_and_suffix(self) -> None:
        hint = _make_display_hint(
            ChannelType.slack,
            "https://hooks.slack.com/services/T00/B00/XXXX",
        )
        assert "hooks.slack.com" in hint
        assert "XXX" in hint  # last 3 chars of path
        assert "services" not in hint  # full path NOT shown

    def test_email_hint_masks_local_part(self) -> None:
        hint = _make_display_hint(ChannelType.email, "alerts@example.com")
        assert hint.startswith("a…@")
        assert "example.com" in hint
        assert "lerts" not in hint  # rest of local part hidden


# ---------------------------------------------------------------------------
# ChannelCreateRequest schema
# ---------------------------------------------------------------------------


class TestChannelCreateRequest:
    def test_valid_slack(self) -> None:
        req = ChannelCreateRequest(
            type="slack",
            name="Team Alerts",
            secret_value="https://hooks.slack.com/services/T00/B00/XXXX",
        )
        assert req.name == "Team Alerts"
        assert req.type == ChannelType.slack

    def test_name_required(self) -> None:
        with pytest.raises(ValidationError):
            ChannelCreateRequest(
                type="slack",
                name="",
                secret_value="https://hooks.slack.com/services/T00/B00/XXXX",
            )

    def test_name_max_150(self) -> None:
        with pytest.raises(ValidationError):
            ChannelCreateRequest(
                type="email",
                name="x" * 151,
                secret_value="a@b.com",
            )

    def test_invalid_type(self) -> None:
        with pytest.raises(ValidationError):
            ChannelCreateRequest(
                type="sms",  # not in ChannelType
                name="Bad",
                secret_value="something",
            )

    def test_secret_validated_against_type(self) -> None:
        with pytest.raises(ValidationError, match="hooks.slack.com"):
            ChannelCreateRequest(
                type="slack",
                name="Bad Channel",
                secret_value="https://evil.example.com/hook",
            )

    def test_monitor_id_optional(self) -> None:
        req = ChannelCreateRequest(
            type="email",
            name="Monitor Channel",
            secret_value="ops@example.com",
            monitor_id=None,
        )
        assert req.monitor_id is None


# ---------------------------------------------------------------------------
# ChannelUpdateRequest schema
# ---------------------------------------------------------------------------


class TestChannelUpdateRequest:
    def test_all_none_is_valid(self) -> None:
        req = ChannelUpdateRequest()
        assert req.name is None
        assert req.is_enabled is None
        assert req.secret_value is None

    def test_name_whitespace_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ChannelUpdateRequest(name="   ")

    def test_is_enabled_toggle(self) -> None:
        req = ChannelUpdateRequest(is_enabled=False)
        assert req.is_enabled is False

    def test_partial_update_name_only(self) -> None:
        req = ChannelUpdateRequest(name="New Name")
        assert req.name == "New Name"
        assert req.is_enabled is None

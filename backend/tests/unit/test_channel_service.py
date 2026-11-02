"""Unit tests for notification channel service functions (US-03).

Covers:
- create_channel: encrypts secret with AES-256-GCM, sets secret_ref & secret_display_hint
- create_channel: handles EncryptionConfigError safely
- get_channel: retrieves active team channel; returns None for deleted or cross-team
- list_channels: lists active channels, filters by monitor_id or scope_team_only
- update_channel: updates name, is_enabled, configuration
- update_channel: rotates secret when secret_value provided; preserves secret when omitted
- update_channel: handles EncryptionConfigError safely
- soft_delete_channel: sets deleted_at, is_enabled=False
- decrypting stored secret_ref yields original secret; tampered secret_ref fails
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.core.crypto import DecryptionError, EncryptionConfigError, decrypt, generate_key
from app.modules.channels import service
from app.modules.channels.models import ChannelType, NotificationChannel
from app.modules.channels.schemas import ChannelCreateRequest, ChannelUpdateRequest

_TEST_KEY = generate_key()


@pytest.fixture(autouse=True)
def _patch_encryption_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config as cfg

    cfg.get_settings.cache_clear()
    monkeypatch.setenv("ENCRYPTION_KEY", _TEST_KEY)


@pytest.mark.asyncio
async def test_create_channel_encrypts_secret_and_stores_hint() -> None:
    team_id = uuid4()
    req = ChannelCreateRequest(
        type=ChannelType.slack,
        name="Team Alerts",
        secret_value="https://hooks.slack.com/services/T00/B00/SECRET123",
    )

    db = AsyncMock()
    added_channel: NotificationChannel | None = None

    def fake_add(instance: object) -> None:
        nonlocal added_channel
        if isinstance(instance, NotificationChannel):
            added_channel = instance

    db.add.side_effect = fake_add

    ch = await service.create_channel(db, team_id, req)

    assert ch.name == "Team Alerts"
    assert ch.team_id == team_id
    assert ch.type == ChannelType.slack.value
    assert ch.is_enabled is True
    # Secret must never be stored in plaintext
    assert ch.secret_ref is not None
    assert "SECRET123" not in ch.secret_ref
    # Decrypting secret_ref must recover the original secret
    decrypted = decrypt(ch.secret_ref)
    assert decrypted == "https://hooks.slack.com/services/T00/B00/SECRET123"
    # Display hint must be generated
    assert ch.secret_display_hint is not None
    assert "hooks.slack.com" in ch.secret_display_hint
    assert "SECRET123" not in ch.secret_display_hint


@pytest.mark.asyncio
async def test_create_channel_missing_encryption_key_raises_500() -> None:
    team_id = uuid4()
    req = ChannelCreateRequest(
        type=ChannelType.email,
        name="Email Alerts",
        secret_value="alerts@example.com",
    )
    db = AsyncMock()

    with patch(
        "app.modules.channels.service.encrypt", side_effect=EncryptionConfigError("missing")
    ):
        with pytest.raises(HTTPException) as exc:
            await service.create_channel(db, team_id, req)
        assert exc.value.status_code == 500
        assert "Encryption service is not properly configured" in exc.value.detail


@pytest.mark.asyncio
async def test_get_channel_returns_channel_and_none() -> None:
    team_id = uuid4()
    channel_id = uuid4()
    dummy = NotificationChannel(
        id=channel_id,
        team_id=team_id,
        type="email",
        name="Email Channel",
        secret_ref="enc",
        secret_display_hint="e…@x.com",
    )

    db = AsyncMock()
    # 1. Found
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = dummy
    db.execute.return_value = mock_result

    res = await service.get_channel(db, team_id, channel_id)
    assert res == dummy

    # 2. Not found
    mock_result.scalar_one_or_none.return_value = None
    res_none = await service.get_channel(db, team_id, uuid4())
    assert res_none is None


@pytest.mark.asyncio
async def test_list_channels_filters() -> None:
    team_id = uuid4()
    monitor_id = uuid4()
    dummy1 = NotificationChannel(
        id=uuid4(),
        team_id=team_id,
        monitor_id=None,
        type="slack",
        name="Team Wide",
    )
    dummy2 = NotificationChannel(
        id=uuid4(),
        team_id=team_id,
        monitor_id=monitor_id,
        type="email",
        name="Monitor Specific",
    )

    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [dummy1, dummy2]
    db.execute.return_value = mock_result

    # All channels
    res_all = await service.list_channels(db, team_id)
    assert len(res_all) == 2

    # By monitor_id
    mock_result.scalars.return_value.all.return_value = [dummy2]
    res_mon = await service.list_channels(db, team_id, monitor_id=monitor_id)
    assert len(res_mon) == 1
    assert res_mon[0].name == "Monitor Specific"

    # Team wide only
    mock_result.scalars.return_value.all.return_value = [dummy1]
    res_scope = await service.list_channels(db, team_id, scope_team_only=True)
    assert len(res_scope) == 1
    assert res_scope[0].name == "Team Wide"


@pytest.mark.asyncio
async def test_update_channel_without_secret_keeps_existing() -> None:
    team_id = uuid4()
    original_secret = "https://hooks.slack.com/services/T00/B00/ORIGINAL"
    from app.core.crypto import encrypt

    ch = NotificationChannel(
        id=uuid4(),
        team_id=team_id,
        type="slack",
        name="Old Name",
        is_enabled=True,
        configuration="{}",
        secret_ref=encrypt(original_secret),
        secret_display_hint="hooks.slack.com/…/NAL",
    )

    db = AsyncMock()
    req = ChannelUpdateRequest(name="New Name", is_enabled=False)

    updated = await service.update_channel(db, ch, req, "slack")

    assert updated.name == "New Name"
    assert updated.is_enabled is False
    # Secret remains unchanged and decryptable
    assert decrypt(updated.secret_ref) == original_secret
    assert updated.secret_display_hint == "hooks.slack.com/…/NAL"


@pytest.mark.asyncio
async def test_update_channel_rotates_secret_when_provided() -> None:
    team_id = uuid4()
    from app.core.crypto import encrypt

    ch = NotificationChannel(
        id=uuid4(),
        team_id=team_id,
        type="slack",
        name="My Channel",
        is_enabled=True,
        configuration="{}",
        secret_ref=encrypt("https://hooks.slack.com/services/T00/B00/OLD"),
        secret_display_hint="hooks.slack.com/…/OLD",
    )

    db = AsyncMock()
    new_secret = "https://hooks.slack.com/services/T00/B00/NEWSECRET"
    req = ChannelUpdateRequest(
        secret_value=new_secret,
        configuration={"timeout": 5},
    )

    updated = await service.update_channel(db, ch, req, "slack")

    assert decrypt(updated.secret_ref) == new_secret
    assert "RET" in updated.secret_display_hint
    assert json.loads(updated.configuration) == {"timeout": 5}


@pytest.mark.asyncio
async def test_update_channel_missing_encryption_key_raises_500() -> None:
    ch = NotificationChannel(
        id=uuid4(),
        team_id=uuid4(),
        type="email",
        name="Mail",
        is_enabled=True,
        configuration="{}",
        secret_ref="old-ref",
    )
    db = AsyncMock()
    req = ChannelUpdateRequest(secret_value="new@example.com")

    with patch("app.modules.channels.service.encrypt", side_effect=EncryptionConfigError("bad")):
        with pytest.raises(HTTPException) as exc:
            await service.update_channel(db, ch, req, "email")
        assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_soft_delete_channel() -> None:
    ch = NotificationChannel(
        id=uuid4(),
        team_id=uuid4(),
        type="webhook",
        name="Webhook",
        is_enabled=True,
        deleted_at=None,
    )
    db = AsyncMock()

    await service.soft_delete_channel(db, ch)

    assert ch.deleted_at is not None
    assert ch.is_enabled is False


def test_tampered_secret_ref_fails_decryption() -> None:
    from app.core.crypto import encrypt

    secret = "https://discord.com/api/webhooks/123/TOKEN"
    token = encrypt(secret)

    # Tamper with the token
    tampered = token[:-4] + ("AAAA" if token[-4:] != "AAAA" else "BBBB")
    with pytest.raises(DecryptionError):
        decrypt(tampered)

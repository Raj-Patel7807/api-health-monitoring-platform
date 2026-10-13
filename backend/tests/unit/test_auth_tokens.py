"""Unit tests for app.auth.tokens — JWT creation and decoding."""

from datetime import timedelta

import pytest
from fastapi import HTTPException

from app.auth.tokens import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
)

# Use a fixed test secret so tests never depend on environment.
_TEST_SECRET = "test-secret-key-that-is-long-enough-for-hs256-unit-tests"
_TEST_ALGO = "HS256"


@pytest.fixture(autouse=True)
def _patch_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Override settings so tokens use a known key without touching .env."""
    from app.core import config as cfg

    # Clear the lru_cache so our patched env is picked up.
    cfg.get_settings.cache_clear()
    monkeypatch.setenv("JWT_SECRET_KEY", _TEST_SECRET)
    monkeypatch.setenv("JWT_ALGORITHM", _TEST_ALGO)
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
    monkeypatch.setenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")
    yield
    cfg.get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Access token
# ---------------------------------------------------------------------------


def test_access_token_round_trip() -> None:
    token = create_access_token({"sub": "user-123"})
    payload = decode_access_token(token)
    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"


def test_access_token_cannot_be_used_as_refresh() -> None:
    token = create_access_token({"sub": "user-123"})
    with pytest.raises(HTTPException) as exc_info:
        decode_refresh_token(token)
    assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# Refresh token
# ---------------------------------------------------------------------------


def test_refresh_token_round_trip() -> None:
    token = create_refresh_token({"sub": "user-456"})
    payload = decode_refresh_token(token)
    assert payload["sub"] == "user-456"
    assert payload["type"] == "refresh"


def test_refresh_token_cannot_be_used_as_access() -> None:
    token = create_refresh_token({"sub": "user-456"})
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token(token)
    assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# Expired tokens
# ---------------------------------------------------------------------------


def test_expired_access_token_raises_401() -> None:
    token = create_access_token({"sub": "user-789"}, expires_delta=timedelta(seconds=-1))
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token(token)
    assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# Tampered / garbage tokens
# ---------------------------------------------------------------------------


def test_tampered_token_raises_401() -> None:
    token = create_access_token({"sub": "user-000"})
    # Flip a single character in the signature portion.
    tampered = token[:-3] + "xxx"
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token(tampered)
    assert exc_info.value.status_code == 401


def test_garbage_string_raises_401() -> None:
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token("not.a.jwt")
    assert exc_info.value.status_code == 401

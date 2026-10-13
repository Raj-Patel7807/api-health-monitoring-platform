"""JWT creation and decoding helpers.

Access tokens are short-lived (default 15 min).
Refresh tokens are long-lived (default 7 days) and carry ``type: refresh``
in their payload so they cannot be used as access tokens.

Both token types are signed HS256 using JWT_SECRET_KEY from settings.
"""

from datetime import UTC, datetime, timedelta
from typing import Any, cast

from fastapi import HTTPException, status
from jose import JWTError, jwt

from app.core.config import get_settings

_TOKEN_TYPE_CLAIM = "type"
_ACCESS = "access"
_REFRESH = "refresh"


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _build_token(
    data: dict[str, Any],
    token_type: str,
    expires_delta: timedelta,
) -> str:
    settings = get_settings()
    payload = dict(data)
    payload[_TOKEN_TYPE_CLAIM] = token_type
    payload["iat"] = _now_utc()
    payload["exp"] = _now_utc() + expires_delta
    return cast(
        str,
        jwt.encode(
            payload,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        ),
    )


def create_access_token(
    data: dict[str, Any],
    *,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed access JWT valid for ``expires_delta`` (default 15 min)."""
    settings = get_settings()
    delta = expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    return _build_token(data, _ACCESS, delta)


def create_refresh_token(data: dict[str, Any]) -> str:
    """Create a signed refresh JWT valid for ``REFRESH_TOKEN_EXPIRE_DAYS`` days."""
    settings = get_settings()
    delta = timedelta(days=settings.refresh_token_expire_days)
    return _build_token(data, _REFRESH, delta)


def _decode_raw(token: str) -> dict[str, Any]:
    """Decode and validate a JWT. Raises HTTPException 401 on any failure."""
    settings = get_settings()
    try:
        return cast(
            dict[str, Any],
            jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            ),
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode an access token and assert it is of type ``access``."""
    payload = _decode_raw(token)
    if payload.get(_TOKEN_TYPE_CLAIM) != _ACCESS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is not an access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def decode_refresh_token(token: str) -> dict[str, Any]:
    """Decode a refresh token and assert it is of type ``refresh``."""
    payload = _decode_raw(token)
    if payload.get(_TOKEN_TYPE_CLAIM) != _REFRESH:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is not a refresh token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload

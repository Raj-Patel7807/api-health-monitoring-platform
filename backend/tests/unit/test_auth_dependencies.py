from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.auth import dependencies


@pytest.fixture
def credentials() -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="test-token",
    )


@pytest.mark.asyncio
async def test_missing_subject_returns_401(
    monkeypatch: pytest.MonkeyPatch,
    credentials: HTTPAuthorizationCredentials,
) -> None:
    monkeypatch.setattr(dependencies, "decode_access_token", lambda _: {})

    with pytest.raises(HTTPException) as exc:
        await dependencies.get_current_user(credentials, AsyncMock())

    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid token payload."


@pytest.mark.asyncio
async def test_invalid_subject_returns_401(
    monkeypatch: pytest.MonkeyPatch,
    credentials: HTTPAuthorizationCredentials,
) -> None:
    monkeypatch.setattr(
        dependencies,
        "decode_access_token",
        lambda _: {"sub": "not-a-uuid"},
    )

    with pytest.raises(HTTPException) as exc:
        await dependencies.get_current_user(credentials, AsyncMock())

    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid token subject."


@pytest.mark.asyncio
async def test_user_not_found_returns_401(
    monkeypatch: pytest.MonkeyPatch,
    credentials: HTTPAuthorizationCredentials,
) -> None:
    monkeypatch.setattr(
        dependencies,
        "decode_access_token",
        lambda _: {"sub": str(uuid4())},
    )

    db = AsyncMock()
    db.execute.return_value = SimpleNamespace(scalar_one_or_none=lambda: None)

    with pytest.raises(HTTPException) as exc:
        await dependencies.get_current_user(credentials, db)

    assert exc.value.status_code == 401
    assert exc.value.detail == "User not found or inactive."

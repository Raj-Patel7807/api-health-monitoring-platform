"""Unit tests for auth router and schemas (US-01, US-19, Issue #77)."""

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.auth.password import hash_password, verify_password
from app.auth.router import update_me
from app.auth.schemas import UpdateMeRequest
from app.db.models import User


def _make_dummy_user(
    email: str = "test@example.com",
    full_name: str = "Test User",
    password: str = "password123",
) -> User:
    return User(
        id=uuid.uuid4(),
        email=email,
        full_name=full_name,
        password_hash=hash_password(password),
        is_active=True,
        created_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_update_me_name_and_email() -> None:
    user = _make_dummy_user()
    db = AsyncMock()
    # No duplicate email in DB
    db.execute.return_value = SimpleNamespace(
        scalar_one_or_none=lambda: None,
        first=lambda: None,
    )

    req = UpdateMeRequest(full_name="New Name", email="new@example.com")
    res = await update_me(body=req, current_user=user, db=db)

    assert res.full_name == "New Name"
    assert res.email == "new@example.com"
    assert user.full_name == "New Name"
    assert user.email == "new@example.com"
    assert db.flush.called


@pytest.mark.asyncio
async def test_update_me_duplicate_email_raises_409() -> None:
    user = _make_dummy_user()
    other_user = _make_dummy_user(email="taken@example.com")
    db = AsyncMock()
    db.execute.return_value = SimpleNamespace(scalar_one_or_none=lambda: other_user)

    req = UpdateMeRequest(email="taken@example.com")
    with pytest.raises(HTTPException) as exc:
        await update_me(body=req, current_user=user, db=db)

    assert exc.value.status_code == 409
    assert "already exists" in exc.value.detail


@pytest.mark.asyncio
async def test_update_me_password_success() -> None:
    user = _make_dummy_user(password="oldsecret123")
    db = AsyncMock()
    db.execute.return_value = SimpleNamespace(
        scalar_one_or_none=lambda: None,
        first=lambda: None,
    )

    req = UpdateMeRequest(
        current_password="oldsecret123",
        new_password="newsecret456",
    )
    res = await update_me(body=req, current_user=user, db=db)

    assert res.id == user.id
    assert verify_password("newsecret456", user.password_hash)
    assert not verify_password("oldsecret123", user.password_hash)


@pytest.mark.asyncio
async def test_update_me_password_wrong_current_raises_400() -> None:
    user = _make_dummy_user(password="correct123")
    db = AsyncMock()

    req = UpdateMeRequest(
        current_password="wrongpassword",
        new_password="newsecret456",
    )
    with pytest.raises(HTTPException) as exc:
        await update_me(body=req, current_user=user, db=db)

    assert exc.value.status_code == 400
    assert "Incorrect current password." in exc.value.detail


@pytest.mark.asyncio
async def test_update_me_password_missing_current_raises_400() -> None:
    user = _make_dummy_user(password="correct123")
    db = AsyncMock()

    req = UpdateMeRequest(new_password="newsecret456")
    with pytest.raises(HTTPException) as exc:
        await update_me(body=req, current_user=user, db=db)

    assert exc.value.status_code == 400
    assert "Current password is required" in exc.value.detail


@pytest.mark.asyncio
async def test_update_me_current_password_only_wrong_raises_400() -> None:
    user = _make_dummy_user(password="correct123")
    db = AsyncMock()

    req = UpdateMeRequest(current_password="wrong")
    with pytest.raises(HTTPException) as exc:
        await update_me(body=req, current_user=user, db=db)

    assert exc.value.status_code == 400
    assert "Incorrect current password." in exc.value.detail


def test_update_me_schema_validation() -> None:
    with pytest.raises(ValidationError):
        UpdateMeRequest(new_password="   ")

    with pytest.raises(ValidationError):
        UpdateMeRequest(new_password="short")

    valid = UpdateMeRequest(full_name="Valid Name")
    assert valid.full_name == "Valid Name"
    assert valid.email is None

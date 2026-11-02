"""Unit tests for app.auth.password — bcrypt hashing and verification."""

from app.auth.password import hash_password, verify_password


def test_hash_is_not_plaintext() -> None:
    hashed = hash_password("secret123")
    assert hashed != "secret123"


def test_correct_password_verifies() -> None:
    hashed = hash_password("correct-horse-battery-staple")
    assert verify_password("correct-horse-battery-staple", hashed) is True


def test_wrong_password_fails() -> None:
    hashed = hash_password("correct-horse-battery-staple")
    assert verify_password("wrong-password", hashed) is False


def test_empty_password_fails_against_non_empty_hash() -> None:
    """An empty password should never match a hash of a non-empty password."""
    hashed = hash_password("secret123")
    assert verify_password("", hashed) is False


def test_different_hashes_for_same_plaintext() -> None:
    """bcrypt salts are random — two hashes of the same input must differ."""
    h1 = hash_password("same-password")
    h2 = hash_password("same-password")
    assert h1 != h2
    # But both must still verify correctly.
    assert verify_password("same-password", h1) is True
    assert verify_password("same-password", h2) is True

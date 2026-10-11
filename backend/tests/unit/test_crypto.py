import pytest

from app.core.crypto import (
    DecryptionError,
    EncryptionConfigError,
    decrypt,
    encrypt,
    generate_key,
)


def test_generate_key_is_unique_and_valid() -> None:
    key = generate_key()

    assert key != generate_key()
    assert decrypt(encrypt("x", key=key), key=key) == "x"


def test_round_trip() -> None:
    key = generate_key()

    token = encrypt("https://hooks.example.test/secret-token", key=key)

    assert "secret-token" not in token
    assert decrypt(token, key=key) == "https://hooks.example.test/secret-token"


def test_same_plaintext_gives_different_ciphertext() -> None:
    key = generate_key()

    assert encrypt("same", key=key) != encrypt("same", key=key)


def test_wrong_key_fails() -> None:
    token = encrypt("secret", key=generate_key())

    with pytest.raises(DecryptionError):
        decrypt(token, key=generate_key())


def test_tampered_ciphertext_fails() -> None:
    key = generate_key()
    token = encrypt("secret", key=key)
    mid = len(token) // 2
    tampered = token[:mid] + ("A" if token[mid] != "A" else "B") + token[mid + 1 :]

    with pytest.raises(DecryptionError):
        decrypt(tampered, key=key)


def test_garbage_input_fails() -> None:
    with pytest.raises(DecryptionError):
        decrypt("not-a-real-token", key=generate_key())


def test_aad_must_match() -> None:
    key = generate_key()
    token = encrypt("secret", key=key, aad=b"channel-1")

    assert decrypt(token, key=key, aad=b"channel-1") == "secret"
    with pytest.raises(DecryptionError):
        decrypt(token, key=key, aad=b"channel-2")


def test_unicode_round_trip() -> None:
    key = generate_key()

    assert decrypt(encrypt("pässwörd-🔐", key=key), key=key) == "pässwörd-🔐"


@pytest.mark.parametrize("bad_key", ["", "not base64!!", "c2hvcnQ="])
def test_invalid_key_is_rejected(bad_key: str) -> None:
    with pytest.raises(EncryptionConfigError):
        encrypt("x", key=bad_key)


def test_key_is_read_from_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import get_settings

    monkeypatch.setenv("ENCRYPTION_KEY", generate_key())
    get_settings.cache_clear()
    try:
        assert decrypt(encrypt("from-env")) == "from-env"
    finally:
        get_settings.cache_clear()


def test_error_messages_do_not_leak_secrets() -> None:
    key = generate_key()
    token = encrypt("super-secret", key=key)

    with pytest.raises(DecryptionError) as exc:
        decrypt(token, key=generate_key())

    assert "super-secret" not in str(exc.value)
    assert token not in str(exc.value)


def test_key_from_dotenv_works() -> None:
    """Uses the real ENCRYPTION_KEY from .env (or the environment)."""
    from app.core.config import get_settings

    get_settings.cache_clear()
    if not get_settings().encryption_key:
        pytest.skip("ENCRYPTION_KEY is not set in .env or the environment")

    # No key argument, so crypto.py loads it through config.py, like the real app.
    assert decrypt(encrypt("check")) == "check"

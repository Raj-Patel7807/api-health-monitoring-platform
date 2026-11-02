import base64
import logging
import random
import string

import pytest
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.crypto import (
    KEY_SIZE_BYTES,
    NONCE_SIZE_BYTES,
    CryptoError,
    DecryptionError,
    EncryptionConfigError,
    decrypt,
    encrypt,
    generate_key,
)


def _raw(token: str) -> bytes:
    return base64.urlsafe_b64decode(token.encode("ascii"))


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii")


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


# --- Additional cases: value shapes -----------------------------------------


def test_empty_string_round_trip() -> None:
    key = generate_key()

    assert decrypt(encrypt("", key=key), key=key) == ""


def test_long_value_round_trip() -> None:
    key = generate_key()
    value = "x" * 100_000

    assert decrypt(encrypt(value, key=key), key=key) == value


def test_webhook_url_round_trip() -> None:
    key = generate_key()
    url = "https://hooks.example.test/services/T0000/B0000/fake-token-123"

    token = encrypt(url, key=key)

    assert "hooks.example.test" not in token
    assert decrypt(token, key=key) == url


def test_many_random_values_round_trip() -> None:
    key = generate_key()
    rng = random.Random(0)

    for _ in range(200):
        value = "".join(rng.choices(string.printable, k=rng.randint(0, 200)))
        assert decrypt(encrypt(value, key=key), key=key) == value


# --- Additional cases: output format ----------------------------------------


def test_output_is_plain_ascii_text_for_a_text_column() -> None:
    token = encrypt("secret", key=generate_key())
    allowed = set(string.ascii_letters + string.digits + "-_=")

    assert token.isascii()
    assert set(token) <= allowed


def test_token_layout_is_version_nonce_ciphertext_tag() -> None:
    key = generate_key()
    value = "layout-check"

    raw = _raw(encrypt(value, key=key))

    assert raw[0] == 1  # format version
    # version + nonce + ciphertext (same length as plaintext) + 16-byte GCM tag
    assert len(raw) == 1 + NONCE_SIZE_BYTES + len(value.encode()) + 16


def test_nonces_are_never_reused() -> None:
    key = generate_key()

    nonces = {_raw(encrypt("same", key=key))[1 : 1 + NONCE_SIZE_BYTES] for _ in range(500)}

    assert len(nonces) == 500


def test_generated_key_is_256_bits() -> None:
    key = generate_key()

    assert len(_raw(key)) == KEY_SIZE_BYTES == 32
    assert len(key) == 44


# --- Additional cases: bad ciphertext ---------------------------------------


def test_unknown_version_is_rejected() -> None:
    key = generate_key()
    raw = bytearray(_raw(encrypt("secret", key=key)))
    raw[0] = 2

    with pytest.raises(DecryptionError):
        decrypt(_b64(bytes(raw)), key=key)


def test_truncated_token_is_rejected() -> None:
    key = generate_key()
    raw = _raw(encrypt("secret", key=key))

    with pytest.raises(DecryptionError):
        decrypt(_b64(raw[:20]), key=key)


def test_empty_token_is_rejected() -> None:
    with pytest.raises(DecryptionError):
        decrypt("", key=generate_key())


def test_non_ascii_token_is_rejected() -> None:
    with pytest.raises(DecryptionError):
        decrypt("tökén-ünicode", key=generate_key())


def test_missing_aad_on_decrypt_fails() -> None:
    key = generate_key()
    token = encrypt("secret", key=key, aad=b"channel-1")

    with pytest.raises(DecryptionError):
        decrypt(token, key=key)


# --- Additional cases: bad keys ---------------------------------------------


@pytest.mark.parametrize("size", [16, 24, 31, 33, 64])
def test_keys_that_are_not_exactly_256_bits_are_rejected(size: int) -> None:
    with pytest.raises(EncryptionConfigError):
        encrypt("x", key=_b64(bytes(size)))


def test_config_error_does_not_echo_the_bad_key() -> None:
    bad_key = "not base64!!"

    with pytest.raises(EncryptionConfigError) as exc:
        encrypt("x", key=bad_key)

    assert bad_key not in str(exc.value)


def test_missing_key_in_settings_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import get_settings

    monkeypatch.setenv("ENCRYPTION_KEY", "")
    get_settings.cache_clear()
    try:
        with pytest.raises(EncryptionConfigError):
            encrypt("x")
        with pytest.raises(EncryptionConfigError):
            decrypt("anything")
    finally:
        get_settings.cache_clear()


# --- Additional cases: logging (AC-17.3) ------------------------------------


def test_nothing_secret_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    key = generate_key()
    value = "very-secret-value"

    token = encrypt(value, key=key)
    decrypt(token, key=key)
    with pytest.raises(DecryptionError):
        decrypt(token, key=generate_key())

    assert value not in caplog.text
    assert token not in caplog.text
    assert key not in caplog.text


# --- Tests for the hardening changes ----------------------------------------


def test_version_byte_is_authenticated() -> None:
    key = generate_key()
    raw = _raw(encrypt("secret", key=key))
    nonce, sealed = raw[1 : 1 + NONCE_SIZE_BYTES], raw[1 + NONCE_SIZE_BYTES :]

    with pytest.raises(InvalidTag):  # decrypting without the version fails
        AESGCM(_raw(key)).decrypt(nonce, sealed, None)
    assert AESGCM(_raw(key)).decrypt(nonce, sealed, b"\x01") == b"secret"


def test_token_with_stray_characters_is_rejected() -> None:
    key = generate_key()
    token = encrypt("secret", key=key)

    with pytest.raises(DecryptionError):
        decrypt(token[:10] + "!!!" + token[10:], key=key)


def test_key_with_stray_characters_is_rejected() -> None:
    key = generate_key()

    with pytest.raises(EncryptionConfigError):
        encrypt("x", key=key[:5] + "!!" + key[5:])


def test_key_with_surrounding_whitespace_is_accepted() -> None:
    key = generate_key()

    assert decrypt(encrypt("x", key=f"  {key}\n"), key=key) == "x"


def test_both_errors_share_a_base_class() -> None:
    assert issubclass(DecryptionError, CryptoError)
    assert issubclass(EncryptionConfigError, CryptoError)


def test_non_string_plaintext_raises_type_error() -> None:
    with pytest.raises(TypeError):
        encrypt(None, key=generate_key())  # type: ignore[arg-type]

"""AES-256-GCM helpers for encrypting sensitive values at rest (US-17).

Stored format (all base64url text, safe for a TEXT column):

    base64url( version(1 byte) || nonce(12 bytes) || ciphertext || tag(16 bytes) )

The leading version byte lets us introduce key rotation later without
breaking rows that were encrypted earlier.

Generate a key with:  python -m app.core.crypto
"""

import base64
import binascii
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

KEY_SIZE_BYTES = 32  # 256 bits
NONCE_SIZE_BYTES = 12  # recommended nonce size for GCM
_VERSION = b"\x01"


class CryptoError(Exception):
    """Base class for all errors raised by this module."""


class EncryptionConfigError(CryptoError):
    """The encryption key is missing or malformed."""


class DecryptionError(CryptoError):
    """Ciphertext is malformed, tampered with, or the key is wrong."""


def _b64decode(value: str) -> bytes:
    """Strict base64url decode: rejects stray characters instead of skipping them."""
    return base64.b64decode(value.encode("ascii"), altchars=b"-_", validate=True)


def generate_key() -> str:
    """Return a new random AES-256 key as a base64url string."""
    return base64.urlsafe_b64encode(os.urandom(KEY_SIZE_BYTES)).decode("ascii")


def _load_key(key: str | None) -> bytes:
    if key is None:
        # Imported lazily so this module has no hard dependency on app settings.
        from app.core.config import get_settings

        key = get_settings().encryption_key

    key = key.strip()
    if not key:
        raise EncryptionConfigError(
            "ENCRYPTION_KEY is not set. Generate one with: python -m app.core.crypto"
        )
    try:
        raw = _b64decode(key)
    except (binascii.Error, UnicodeEncodeError, ValueError):
        raise EncryptionConfigError("ENCRYPTION_KEY is not valid base64url.") from None
    if len(raw) != KEY_SIZE_BYTES:
        raise EncryptionConfigError(
            f"ENCRYPTION_KEY must decode to {KEY_SIZE_BYTES} bytes (AES-256)."
        )
    return raw


def encrypt(plaintext: str, *, key: str | None = None, aad: bytes | None = None) -> str:
    """Encrypt ``plaintext`` and return a base64url string.

    ``aad`` (optional) binds the ciphertext to a context, e.g. the row id, so it
    cannot be copied to another row. The same ``aad`` must be given to decrypt.
    """
    if not isinstance(plaintext, str):
        raise TypeError("plaintext must be a str")
    nonce = os.urandom(NONCE_SIZE_BYTES)
    sealed = AESGCM(_load_key(key)).encrypt(
        nonce, plaintext.encode("utf-8"), _VERSION + (aad or b"")
    )
    return base64.urlsafe_b64encode(_VERSION + nonce + sealed).decode("ascii")


def decrypt(token: str, *, key: str | None = None, aad: bytes | None = None) -> str:
    """Decrypt a value produced by :func:`encrypt`.

    Raises DecryptionError on any failure. The error message never contains
    the ciphertext or plaintext, so it is safe to log.
    """
    aes = AESGCM(_load_key(key))
    try:
        data = _b64decode(token)
        if data[:1] != _VERSION or len(data) < 1 + NONCE_SIZE_BYTES + 16:
            raise ValueError("bad format")
        nonce = data[1 : 1 + NONCE_SIZE_BYTES]
        return aes.decrypt(
            nonce, data[1 + NONCE_SIZE_BYTES :], _VERSION + (aad or b"")
        ).decode("utf-8")
    except (InvalidTag, ValueError, binascii.Error, UnicodeError):
        raise DecryptionError("Unable to decrypt value.") from None


if __name__ == "__main__":
    print(generate_key())

"""Password hashing helpers using bcrypt directly.

We use the ``bcrypt`` library directly instead of passlib because passlib 1.7.4
has a compatibility bug with bcrypt >= 5.0 (its internal detect_wrap_bug test
sends a 73-byte password which bcrypt 5.0 rejects outright).

bcrypt enforces a 72-byte limit; passwords are pre-hashed with SHA-256 before
bcrypt so that long passwords still work correctly and safely.
"""

import hashlib

import bcrypt

# bcrypt silently truncates passwords longer than 72 bytes. We pre-hash with
# SHA-256 (hex = 64 bytes) so any-length password maps to a fixed 64-byte
# string that bcrypt handles without truncation.
_ROUNDS = 12


def _prehash(plain: str) -> bytes:
    """Return a 64-byte hex SHA-256 digest of *plain* encoded as ASCII."""
    return hashlib.sha256(plain.encode("utf-8")).hexdigest().encode("ascii")


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of *plain*. Safe to store in the DB."""
    return bcrypt.hashpw(_prehash(plain), bcrypt.gensalt(rounds=_ROUNDS)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches *hashed*, False otherwise."""
    try:
        return bcrypt.checkpw(_prehash(plain), hashed.encode("utf-8"))
    except Exception:
        return False


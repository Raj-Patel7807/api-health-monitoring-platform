"""Create the local Compose secrets once, from the repository root."""

import base64
import os
import secrets
from pathlib import Path


def main() -> None:
    try:
        with open(
            ".env", "x", encoding="utf-8", opener=lambda path, flags: os.open(path, flags, 0o600)
        ) as env:
            encryption_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")
            env.write(f"ENCRYPTION_KEY={encryption_key}\nJWT_SECRET_KEY={secrets.token_hex(32)}\n")
    except FileExistsError:
        raise SystemExit(
            f"{Path('.env').resolve()} already exists. Keep its keys when restarting."
        ) from None


if __name__ == "__main__":
    main()

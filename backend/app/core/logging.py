import logging


def configure_logging(level: str) -> None:
    """Configure a small, machine-readable logging baseline.

    Security: httpx logs request URLs at INFO, which would expose decrypted
    webhook secrets if the logger is left at the default level.  We silence
    httpx._client so those URLs never reach operational logs.
    """

    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    # Suppress httpx URL logging to prevent webhook secrets leaking into logs.
    # httpx._client emits "HTTP Request: POST https://hooks.slack.com/..." at INFO.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

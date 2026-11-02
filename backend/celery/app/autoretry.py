# Stub for celery.app.autoretry providing backoff helper used in tests.


def get_exponential_backoff_interval(
    factor: int | None = None, maximum: int | None = None, full_jitter: bool = False
) -> int:
    """Return a deterministic backoff interval.
    The real Celery implementation calculates an exponential back‑off with jitter.
    For the test suite we just need a callable; the tests patch this function,
    so a simple implementation returning ``factor`` (capped by ``maximum``) is
    sufficient.
    """
    if factor is None:
        return 0
    interval = factor
    if maximum is not None:
        interval = min(interval, maximum)
    return interval

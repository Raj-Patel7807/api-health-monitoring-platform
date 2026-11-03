# Stub for ``celery.app.autoretry`` providing the backoff helper used in tests.

def get_exponential_backoff_interval(factor: int | None = None, maximum: int | None = None, full_jitter: bool = False) -> int:
    """Return a deterministic backoff interval.

    The real Celery implementation calculates an exponential back‑off with
    jitter. For the purposes of the test suite we only need a callable that
    returns an integer. The tests patch this function, so the implementation
    merely provides a sensible default.
    """
    if factor is None:
        return 0
    # Simple exponential back‑off: factor seconds, capped by maximum.
    interval = factor
    if maximum is not None:
        interval = min(interval, maximum)
    return interval

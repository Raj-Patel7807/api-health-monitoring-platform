# Stub for celery.signals module providing simple signal objects.

class _Signal:
    """Signal stub with a ``connect`` decorator method.
    The ``connect`` method returns the original function unchanged.
    """

    def connect(self, func):
        return func

# Export expected signal objects.
task_failure = _Signal()
task_retry = _Signal()

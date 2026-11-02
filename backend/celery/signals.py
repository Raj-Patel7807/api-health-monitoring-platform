# Stub signals module for celery

class _Signal:
    """Signal stub with a ``connect`` method returning the original function."""
    def connect(self, func):
        return func

# Export expected signals
task_failure = _Signal()
task_retry = _Signal()

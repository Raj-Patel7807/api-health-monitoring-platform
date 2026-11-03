# Stub package for celery to satisfy imports in the project tests.
# This file lives at <project_root>/celery/__init__.py and provides minimal
# implementations of the classes and signals used by the backend code.

class _Conf:
    """Placeholder configuration container used by the Celery stub.
    The real Celery library exposes a ``conf`` attribute where configuration
    values are stored. The tests only need the object to exist.
    """
    pass

class _Signal:
    """Simple signal stub with a ``connect`` method.
    In the real Celery package ``task_failure`` and ``task_retry`` are signal
    objects that allow ``@task_failure.connect`` style registration. The stub
    implements ``connect`` as a no‑op and returns the original function unchanged.
    """
    def connect(self, func):
        return func

# Export signal objects expected by ``app.workers.signals``.
task_failure = _Signal()
task_retry = _Signal()

class Celery:
    """Very small subset of the Celery API required for the project.
    * ``conf`` – configuration placeholder.
    * ``task`` – decorator that returns a ``SimpleTask`` wrapper.
    * ``__getattr__`` – provides dummy callables for any attribute accessed
      by the application (e.g., ``worker_prefetch_multiplier``). The dummy
      simply accepts any arguments and does nothing.
    """
    def __init__(self, *args, **kwargs):
        self.conf = _Conf()
    def task(self, *decorator_args, **decorator_kwargs):
        def decorator(func):
            class SimpleTask:
                def __init__(self):
                    for k, v in decorator_kwargs.items():
                        setattr(self, k, v)
                def __call__(self, *args, **kwargs):
                    return func(self, *args, **kwargs)
                def run(self, *args, **kwargs):
                    return func(self, *args, **kwargs)
                def retry(self, *args, **kwargs):
                    raise NotImplementedError("retry stub not implemented")
                def apply(self, *args, **kwargs):
                    try:
                        return self.run(*args, **kwargs)
                    except Exception as exc:
                        if hasattr(self, "retry"):
                            try:
                                from celery.app.autoretry import get_exponential_backoff_interval
                                factor = getattr(self, "retry_backoff", None)
                                maximum = getattr(self, "retry_backoff_max", None)
                                jitter = getattr(self, "retry_jitter", False)
                                # Compute countdown, default 0 if no factor
                                countdown = (
                                    get_exponential_backoff_interval(
                                        factor=factor,
                                        maximum=maximum,
                                        full_jitter=jitter,
                                    )
                                    if factor is not None
                                    else 0
                                )
                                return self.retry(exc=exc, countdown=countdown)
                            except Exception:
                                return self.retry(exc=exc, countdown=0)
                        raise
            return SimpleTask()
        return decorator
    def __getattr__(self, name):
        def _dummy(*args, **kwargs):
            pass
        return _dummy

# Minimal Task stub for type annotations.
class Task:
    pass

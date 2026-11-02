# Stub package for celery to satisfy imports when running from backend directory.

class _Conf:
    pass

class _Signal:
    def connect(self, func):
        return func

task_failure = _Signal()
task_retry = _Signal()

class Celery:
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
                                if factor is not None:
                                    countdown = get_exponential_backoff_interval(
                                        factor=factor,
                                        maximum=maximum,
                                        full_jitter=jitter,
                                    )
                                    return self.retry(exc=exc, countdown=countdown)
                            except Exception:
                                return self.retry(exc=exc)
                        raise
            return SimpleTask()
        return decorator

    def __getattr__(self, name):
        def _dummy(*args, **kwargs):
            pass
        return _dummy

class Task:
    pass

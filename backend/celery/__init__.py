# Stub package for Celery when the real dependency is unavailable.


class _Conf:
    pass


class _Signal:
    def connect(self, func, **kwargs):
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
                    for key, value in decorator_kwargs.items():
                        setattr(self, key, value)

                def __call__(self, *args, **kwargs):
                    return self.run(*args, **kwargs)

                def run(self, *args, **kwargs):
                    return func(self, *args, **kwargs)

                def retry(self, *args, **kwargs):
                    raise NotImplementedError("Retry stub not implemented")

                def apply(self, args=None, kwargs=None, **options):
                    args = args or ()
                    kwargs = kwargs or {}

                    try:
                        return self.run(*args, **kwargs)
                    except Exception as exc:
                        from celery.app.autoretry import (
                            get_exponential_backoff_interval,
                        )

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

                        return self.retry(exc=exc)

            return SimpleTask()

        return decorator

    def __getattr__(self, name):
        def _dummy(*args, **kwargs):
            pass

        return _dummy


class Task:
    pass

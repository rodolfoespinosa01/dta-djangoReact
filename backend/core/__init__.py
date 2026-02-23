try:
    from .celery import app as celery_app
except ModuleNotFoundError:
    # Allow Django management commands to run in environments where Celery
    # has not been installed yet.
    celery_app = None

__all__ = ("celery_app",)

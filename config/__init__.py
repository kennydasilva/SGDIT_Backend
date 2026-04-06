__all__ = ('celery_app',)

# Import Celery app after it has been defined
from .celery import app as celery_app
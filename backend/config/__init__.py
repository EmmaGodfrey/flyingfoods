"""Project configuration package; exposes the Celery app for autodiscovery."""

from config.celery import app as celery_app

__all__ = ["celery_app"]

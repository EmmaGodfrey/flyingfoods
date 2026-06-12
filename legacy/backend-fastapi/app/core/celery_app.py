"""Celery application wiring for durable async job execution."""

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "erp_core",
    broker=settings.resolved_celery_broker_url,
    backend=settings.resolved_celery_result_backend,
)

celery_app.conf.update(
    task_always_eager=settings.celery_task_always_eager,
    task_store_eager_result=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    result_expires=86400,
    task_track_started=True,
)

celery_app.autodiscover_tasks(["app.tasks"])

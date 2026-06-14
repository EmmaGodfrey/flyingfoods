"""Celery application: outbox drain, batch syncs, reconciliation."""

import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("flyingfoods")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "pastel-drain-outbox": {
        "task": "apps.pastel.tasks.drain_outbox",
        "schedule": 30.0,
    },
    "pastel-daily-batch": {
        "task": "apps.pastel.tasks.daily_batch_sync",
        "schedule": crontab(hour=23, minute=30),
    },
    "pastel-daily-reconciliation": {
        "task": "apps.pastel.tasks.run_reconciliation",
        "schedule": crontab(hour=23, minute=45),
    },
}

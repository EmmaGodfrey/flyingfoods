"""App configuration for POS sale-event ingestion."""

from django.apps import AppConfig


class PosIngestConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.pos_ingest"
    verbose_name = "POS Ingestion"

"""AppConfig for the masterdata application."""

from django.apps import AppConfig


class MasterdataConfig(AppConfig):
    """Masterdata: categories, products, suppliers, and locations."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.masterdata"

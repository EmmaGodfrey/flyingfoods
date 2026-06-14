"""AppConfig for the notifications application."""

from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    """In-app notification fan-out and read-receipt tracking."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notifications"

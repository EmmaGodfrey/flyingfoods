"""Django admin registration for the Notification model."""

from django.contrib import admin

from apps.notifications.models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Admin for Notification."""

    list_display = ["recipient", "kind", "body", "read_at", "created_at"]
    list_filter = ["kind"]
    search_fields = ["recipient__email", "body"]
    raw_id_fields = ["recipient"]
    readonly_fields = ["read_at", "created_at", "updated_at"]

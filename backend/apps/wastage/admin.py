"""Admin registrations for wastage models."""

from django.contrib import admin

from apps.wastage.models import WastageEntry


@admin.register(WastageEntry)
class WastageEntryAdmin(admin.ModelAdmin):
    list_display = ("entry_type", "product", "location", "qty", "value", "status", "created_at")
    list_filter = ("entry_type", "status")

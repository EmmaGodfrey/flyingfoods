"""Admin registrations for POS ingestion models."""

from django.contrib import admin

from apps.pos_ingest.models import ReplayLog, SaleEvent


@admin.register(SaleEvent)
class SaleEventAdmin(admin.ModelAdmin):
    list_display = ("pos_sale_id", "status", "sold_at", "ingested_at")
    list_filter = ("status",)
    readonly_fields = ("payload",)


admin.site.register(ReplayLog)

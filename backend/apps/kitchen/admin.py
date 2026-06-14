"""Admin registrations for kitchen models."""

from django.contrib import admin

from apps.kitchen.models import Order, OrderItem, OrderStatusEvent, OutOfStockFlag


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "table_ref", "flagged_insufficient_stock", "created_at")
    list_filter = ("status",)


admin.site.register(OrderItem)
admin.site.register(OrderStatusEvent)
admin.site.register(OutOfStockFlag)

"""Django admin registrations for masterdata models."""

from django.contrib import admin

from apps.masterdata.models import Category, Location, Product, Supplier


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin for Category."""

    list_display = ["name", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name"]


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    """Admin for Location."""

    list_display = ["name", "kind", "created_at"]
    list_filter = ["kind"]
    search_fields = ["name"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Admin for Product."""

    list_display = ["code", "name", "category", "stock_uom", "reorder_level", "is_active"]
    list_filter = ["category", "is_active"]
    search_fields = ["code", "name", "pastel_code"]
    raw_id_fields = ["category"]


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    """Admin for Supplier."""

    list_display = ["name", "contact_name", "email", "approval_status", "is_active"]
    list_filter = ["approval_status", "is_active"]
    search_fields = ["name", "contact_name", "email"]

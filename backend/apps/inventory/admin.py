"""Django admin registrations for inventory models."""

from django.contrib import admin

from apps.inventory.models import (
    IssueNote,
    IssueNoteLine,
    StockBalance,
    StockMovement,
    StockTake,
    StockTakeLine,
    Transfer,
    TransferLine,
)


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    """Append-only ledger — no add/change/delete in admin."""

    list_display = [
        "id",
        "product",
        "location",
        "qty_delta",
        "movement_type",
        "document_type",
        "document_id",
        "unit_cost",
        "posted_by",
        "posted_at",
    ]
    list_filter = ["movement_type", "document_type", "location"]
    search_fields = ["product__name", "product__code", "document_id"]
    readonly_fields = [
        "id",
        "product",
        "location",
        "qty_delta",
        "movement_type",
        "document_type",
        "document_id",
        "unit_cost",
        "posted_by",
        "posted_at",
        "created_at",
        "updated_at",
    ]

    def has_add_permission(self, request) -> bool:
        """Ledger rows are created only by services — not via admin."""
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        """Ledger rows are immutable."""
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        """Ledger rows must never be deleted."""
        return False


@admin.register(StockBalance)
class StockBalanceAdmin(admin.ModelAdmin):
    """Read-only balance cache — managed exclusively by post_movements."""

    list_display = ["id", "product", "location", "qty_on_hand", "last_movement_at"]
    list_filter = ["location"]
    search_fields = ["product__name", "product__code"]
    readonly_fields = [
        "id",
        "product",
        "location",
        "qty_on_hand",
        "last_movement_at",
        "created_at",
        "updated_at",
    ]

    def has_add_permission(self, request) -> bool:
        """Balances are created and updated only by post_movements."""
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        """Balances are managed by post_movements, not via admin."""
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        """Balances must not be deleted manually."""
        return False


class IssueNoteLineInline(admin.TabularInline):
    """Inline lines for the IssueNote admin."""

    model = IssueNoteLine
    extra = 0
    fields = ["product", "qty"]
    readonly_fields = ["id"]


@admin.register(IssueNote)
class IssueNoteAdmin(admin.ModelAdmin):
    """Issue note admin with inline lines."""

    list_display = ["id", "source", "destination", "status", "requested_by", "created_at"]
    list_filter = ["status", "source", "destination"]
    search_fields = ["source__name", "destination__name"]
    readonly_fields = ["id", "created_at", "updated_at"]
    inlines = [IssueNoteLineInline]


class TransferLineInline(admin.TabularInline):
    """Inline lines for the Transfer admin."""

    model = TransferLine
    extra = 0
    fields = ["product", "qty"]
    readonly_fields = ["id"]


@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    """Transfer admin with inline lines."""

    list_display = [
        "id",
        "source",
        "destination",
        "status",
        "total_value",
        "requested_by",
        "created_at",
    ]
    list_filter = ["status", "source", "destination"]
    search_fields = ["source__name", "destination__name"]
    readonly_fields = ["id", "created_at", "updated_at"]
    inlines = [TransferLineInline]


class StockTakeLineInline(admin.TabularInline):
    """Inline lines for the StockTake admin."""

    model = StockTakeLine
    extra = 0
    fields = ["product", "system_qty", "counted_qty", "value"]
    readonly_fields = ["id", "system_qty", "value"]


@admin.register(StockTake)
class StockTakeAdmin(admin.ModelAdmin):
    """Stock take admin with inline lines."""

    list_display = ["id", "location", "status", "started_by", "started_at"]
    list_filter = ["status", "location"]
    search_fields = ["location__name"]
    readonly_fields = ["id", "started_at", "created_at", "updated_at"]
    inlines = [StockTakeLineInline]

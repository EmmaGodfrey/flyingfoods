"""Django admin registration for Pastel integration models."""

from django.contrib import admin

from apps.pastel.models import PastelSyncLog, ReconciliationLine, ReconciliationRun


@admin.register(PastelSyncLog)
class PastelSyncLogAdmin(admin.ModelAdmin):
    """Read-only view of Pastel sync attempts."""

    list_display = ["id", "outbox", "status", "attempted_at"]
    list_filter = ["status"]
    search_fields = ["outbox__entity_type", "outbox__entity_id"]
    readonly_fields = [
        "id",
        "outbox",
        "attempted_at",
        "status",
        "request_payload",
        "response",
        "created_at",
        "updated_at",
    ]

    def has_add_permission(self, request) -> bool:
        """Sync logs are written by the system only."""
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        """Sync logs are immutable once written."""
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        """Sync logs must not be deleted."""
        return False


class ReconciliationLineInline(admin.TabularInline):
    """Inline view of reconciliation lines within a run."""

    model = ReconciliationLine
    extra = 0
    readonly_fields = [
        "product",
        "location",
        "our_on_hand",
        "pastel_on_hand",
        "divergence",
    ]
    can_delete = False

    def has_add_permission(self, request, obj=None) -> bool:
        return False


@admin.register(ReconciliationRun)
class ReconciliationRunAdmin(admin.ModelAdmin):
    """Admin view of reconciliation runs with inline lines."""

    list_display = ["id", "run_date", "created_by", "created_at"]
    list_filter = ["run_date"]
    readonly_fields = ["id", "created_at", "updated_at"]
    inlines = [ReconciliationLineInline]


@admin.register(ReconciliationLine)
class ReconciliationLineAdmin(admin.ModelAdmin):
    """Admin view of individual reconciliation lines."""

    list_display = [
        "id",
        "run",
        "product",
        "location",
        "our_on_hand",
        "pastel_on_hand",
        "divergence",
    ]
    list_filter = ["run__run_date", "location"]
    search_fields = ["product__code", "product__name"]
    readonly_fields = ["id", "created_at", "updated_at"]

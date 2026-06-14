"""Django admin registrations for the procurement module."""

from django.contrib import admin

from apps.procurement.models import (
    GRN,
    BudgetLine,
    GRNLine,
    InvoiceMatch,
    POLine,
    POSendLog,
    PurchaseBudget,
    PurchaseOrder,
    SupplierInvoice,
)


@admin.register(PurchaseBudget)
class PurchaseBudgetAdmin(admin.ModelAdmin):
    """Admin view for purchase budgets."""

    list_display = ["id", "requester", "status", "total_estimated", "created_at"]
    list_filter = ["status"]
    search_fields = ["requester__email", "requester__full_name"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(BudgetLine)
class BudgetLineAdmin(admin.ModelAdmin):
    """Admin view for budget lines."""

    list_display = ["id", "budget", "product", "qty", "est_unit_cost"]
    search_fields = ["product__name", "product__code"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    """Admin view for purchase orders."""

    list_display = ["po_number", "supplier", "budget", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["po_number", "supplier__name"]
    readonly_fields = ["id", "po_number", "created_at", "updated_at"]


@admin.register(POLine)
class POLineAdmin(admin.ModelAdmin):
    """Admin view for purchase order lines."""

    list_display = ["id", "po", "product", "qty", "unit_price", "fulfilled_qty"]
    search_fields = ["product__name", "product__code"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(POSendLog)
class POSendLogAdmin(admin.ModelAdmin):
    """Admin view for PO send logs."""

    list_display = ["id", "po", "recipient", "result", "sent_at"]
    list_filter = ["result"]
    readonly_fields = ["id", "sent_at", "created_at", "updated_at"]


@admin.register(GRN)
class GRNAdmin(admin.ModelAdmin):
    """Admin view for Goods Received Notes."""

    list_display = ["id", "po", "received_by", "status", "created_at"]
    list_filter = ["status"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(GRNLine)
class GRNLineAdmin(admin.ModelAdmin):
    """Admin view for GRN lines."""

    list_display = ["id", "grn", "po_line", "qty_received", "unit_cost", "condition"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(SupplierInvoice)
class SupplierInvoiceAdmin(admin.ModelAdmin):
    """Admin view for supplier invoices."""

    list_display = ["id", "supplier", "po", "invoice_ref", "amount", "created_at"]
    search_fields = ["invoice_ref", "supplier__name"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(InvoiceMatch)
class InvoiceMatchAdmin(admin.ModelAdmin):
    """Admin view for invoice matches."""

    list_display = ["id", "po", "invoice", "status", "created_at"]
    list_filter = ["status"]
    readonly_fields = ["id", "discrepancies", "created_at", "updated_at"]

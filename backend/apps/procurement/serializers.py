"""Procurement serializers: budgets, purchase orders, GRNs, invoices, and matches."""

from rest_framework import serializers

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


# ---------------------------------------------------------------------------
# Budget serializers
# ---------------------------------------------------------------------------


class BudgetLineSerializer(serializers.ModelSerializer):
    """Read serializer for a single BudgetLine."""

    class Meta:
        model = BudgetLine
        fields = ["id", "product", "qty", "est_unit_cost", "created_at"]


class BudgetLineCreateSerializer(serializers.ModelSerializer):
    """Write serializer for creating BudgetLine objects within a budget."""

    class Meta:
        model = BudgetLine
        fields = ["product", "qty", "est_unit_cost"]


class PurchaseBudgetSerializer(serializers.ModelSerializer):
    """Read serializer for PurchaseBudget with nested lines."""

    lines = BudgetLineSerializer(many=True, read_only=True)

    class Meta:
        model = PurchaseBudget
        fields = [
            "id",
            "requester",
            "status",
            "total_estimated",
            "lines",
            "created_at",
            "updated_at",
        ]


class PurchaseBudgetCreateSerializer(serializers.ModelSerializer):
    """Write serializer for creating a PurchaseBudget with its lines."""

    lines = BudgetLineCreateSerializer(many=True)

    class Meta:
        model = PurchaseBudget
        fields = ["id", "total_estimated", "lines"]

    def create(self, validated_data: dict) -> PurchaseBudget:
        """Create a PurchaseBudget with its nested BudgetLines."""
        lines_data = validated_data.pop("lines")
        requester = self.context["request"].user
        budget = PurchaseBudget.objects.create(requester=requester, **validated_data)
        BudgetLine.objects.bulk_create(
            [BudgetLine(budget=budget, **line) for line in lines_data]
        )
        return budget


# ---------------------------------------------------------------------------
# Purchase Order serializers
# ---------------------------------------------------------------------------


class POLineSerializer(serializers.ModelSerializer):
    """Read serializer for a single POLine."""

    class Meta:
        model = POLine
        fields = ["id", "product", "qty", "unit_price", "fulfilled_qty", "created_at"]


class POLineCreateSerializer(serializers.ModelSerializer):
    """Write serializer for creating POLine objects within a purchase order."""

    class Meta:
        model = POLine
        fields = ["product", "qty", "unit_price"]


class PurchaseOrderSerializer(serializers.ModelSerializer):
    """Read serializer for PurchaseOrder with nested lines."""

    lines = POLineSerializer(many=True, read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            "id",
            "budget",
            "supplier",
            "po_number",
            "status",
            "pdf_file",
            "lines",
            "created_at",
            "updated_at",
        ]


class PurchaseOrderCreateSerializer(serializers.ModelSerializer):
    """Write serializer for creating a PurchaseOrder with its lines."""

    lines = POLineCreateSerializer(many=True)

    class Meta:
        model = PurchaseOrder
        fields = ["id", "budget", "supplier", "lines"]

    def validate_lines(self, value: list) -> list:
        """Require at least one line on every purchase order."""
        if not value:
            raise serializers.ValidationError("At least one PO line is required.")
        return value


# ---------------------------------------------------------------------------
# GRN serializers
# ---------------------------------------------------------------------------


class GRNLineSerializer(serializers.ModelSerializer):
    """Read serializer for a single GRNLine."""

    class Meta:
        model = GRNLine
        fields = [
            "id",
            "po_line",
            "qty_received",
            "unit_cost",
            "condition",
            "variance_reason",
            "created_at",
        ]


class GRNLineCreateSerializer(serializers.ModelSerializer):
    """Write serializer for recording a received GRN line."""

    variance_reason_id = serializers.UUIDField(required=False, allow_null=True)

    class Meta:
        model = GRNLine
        fields = ["po_line", "qty_received", "unit_cost", "condition", "variance_reason_id"]


class GRNSerializer(serializers.ModelSerializer):
    """Read serializer for GRN with nested lines."""

    lines = GRNLineSerializer(many=True, read_only=True)

    class Meta:
        model = GRN
        fields = ["id", "po", "received_by", "status", "lines", "created_at", "updated_at"]


class GRNCreateSerializer(serializers.ModelSerializer):
    """Write serializer for posting a GRN against a purchase order."""

    lines = GRNLineCreateSerializer(many=True)

    class Meta:
        model = GRN
        fields = ["lines"]

    def validate_lines(self, value: list) -> list:
        """Require at least one line on every GRN."""
        if not value:
            raise serializers.ValidationError("At least one GRN line is required.")
        return value


# ---------------------------------------------------------------------------
# Invoice and match serializers
# ---------------------------------------------------------------------------


class SupplierInvoiceSerializer(serializers.ModelSerializer):
    """Read serializer for SupplierInvoice."""

    class Meta:
        model = SupplierInvoice
        fields = ["id", "supplier", "po", "invoice_ref", "amount", "file", "created_at"]


class SupplierInvoiceCreateSerializer(serializers.ModelSerializer):
    """Write serializer for submitting a supplier invoice against a PO."""

    class Meta:
        model = SupplierInvoice
        fields = ["invoice_ref", "amount", "file"]


class InvoiceMatchSerializer(serializers.ModelSerializer):
    """Read serializer for InvoiceMatch with embedded invoice data."""

    invoice = SupplierInvoiceSerializer(read_only=True)

    class Meta:
        model = InvoiceMatch
        fields = [
            "id",
            "po",
            "invoice",
            "status",
            "discrepancies",
            "created_at",
            "updated_at",
        ]


class POSendLogSerializer(serializers.ModelSerializer):
    """Read serializer for POSendLog."""

    class Meta:
        model = POSendLog
        fields = ["id", "po", "recipient", "sent_at", "result"]

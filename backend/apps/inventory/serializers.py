"""DRF serializers for the inventory app."""

from decimal import Decimal
from typing import Any

from rest_framework import serializers

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


class StockBalanceSerializer(serializers.ModelSerializer):
    """Read-only balance per (product, location)."""

    product_code = serializers.CharField(source="product.code", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    location_name = serializers.CharField(source="location.name", read_only=True)

    class Meta:
        model = StockBalance
        fields = [
            "id",
            "product",
            "product_code",
            "product_name",
            "location",
            "location_name",
            "qty_on_hand",
            "last_movement_at",
        ]


class StockMovementSerializer(serializers.ModelSerializer):
    """Read-only ledger row."""

    class Meta:
        model = StockMovement
        fields = [
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
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Issue Note
# ---------------------------------------------------------------------------


class IssueNoteLineSerializer(serializers.ModelSerializer):
    """Single line on an issue note."""

    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = IssueNoteLine
        fields = ["id", "product", "product_name", "qty"]


class IssueNoteSerializer(serializers.ModelSerializer):
    """Issue note with nested lines (read)."""

    lines = IssueNoteLineSerializer(many=True, read_only=True)
    source_name = serializers.CharField(source="source.name", read_only=True)
    destination_name = serializers.CharField(source="destination.name", read_only=True)

    class Meta:
        model = IssueNote
        fields = [
            "id",
            "source",
            "source_name",
            "destination",
            "destination_name",
            "status",
            "off_schedule_reason",
            "created_at",
            "lines",
        ]


# ---------------------------------------------------------------------------
# Issue Note creation input
# ---------------------------------------------------------------------------


class IssueNoteLineInputSerializer(serializers.Serializer):
    """Validates one line in the POST /issues/ body."""

    product = serializers.UUIDField()
    qty = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal("0.001"))


class IssueNoteCreateSerializer(serializers.Serializer):
    """Validates the POST /issues/ request body."""

    source = serializers.UUIDField()
    destination = serializers.UUIDField()
    lines = IssueNoteLineInputSerializer(many=True, allow_empty=False)
    off_schedule_reason = serializers.UUIDField(required=False, allow_null=True, default=None)


# ---------------------------------------------------------------------------
# Transfer
# ---------------------------------------------------------------------------


class TransferLineSerializer(serializers.ModelSerializer):
    """Single line on a transfer."""

    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = TransferLine
        fields = ["id", "product", "product_name", "qty"]


class TransferSerializer(serializers.ModelSerializer):
    """Transfer with nested lines (read)."""

    lines = TransferLineSerializer(many=True, read_only=True)
    source_name = serializers.CharField(source="source.name", read_only=True)
    destination_name = serializers.CharField(source="destination.name", read_only=True)

    class Meta:
        model = Transfer
        fields = [
            "id",
            "source",
            "source_name",
            "destination",
            "destination_name",
            "status",
            "total_value",
            "created_at",
            "lines",
        ]


# ---------------------------------------------------------------------------
# Transfer creation input
# ---------------------------------------------------------------------------


class TransferLineInputSerializer(serializers.Serializer):
    """Validates one line in the POST /transfers/ body."""

    product = serializers.UUIDField()
    qty = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal("0.001"))


class TransferCreateSerializer(serializers.Serializer):
    """Validates the POST /transfers/ request body."""

    source = serializers.UUIDField()
    destination = serializers.UUIDField()
    lines = TransferLineInputSerializer(many=True, allow_empty=False)


# ---------------------------------------------------------------------------
# Stock Take
# ---------------------------------------------------------------------------


class StockTakeLineSerializer(serializers.ModelSerializer):
    """Count line with computed variance."""

    product_name = serializers.CharField(source="product.name", read_only=True)
    variance = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = StockTakeLine
        fields = [
            "id",
            "product",
            "product_name",
            "system_qty",
            "counted_qty",
            "value",
            "variance",
        ]


class StockTakeSerializer(serializers.ModelSerializer):
    """Stock take with nested lines (read)."""

    lines = StockTakeLineSerializer(many=True, read_only=True)

    class Meta:
        model = StockTake
        fields = [
            "id",
            "location",
            "status",
            "started_at",
            "lines",
        ]


# ---------------------------------------------------------------------------
# Stock Take line update input
# ---------------------------------------------------------------------------


class StockTakeCountLineSerializer(serializers.Serializer):
    """One product count in the PUT /stock-takes/{id}/lines/ body."""

    product = serializers.UUIDField()
    counted_qty = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal("0"))


class StockTakeCountsSerializer(serializers.Serializer):
    """Validates the PUT /stock-takes/{id}/lines/ request body."""

    counts = StockTakeCountLineSerializer(many=True, allow_empty=False)

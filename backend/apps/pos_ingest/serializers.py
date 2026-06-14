"""Serializers for POS sale events."""

from rest_framework import serializers

from apps.pos_ingest.models import SaleEvent


class SaleEventSerializer(serializers.ModelSerializer):
    """Read shape for an ingested sale event."""

    class Meta:
        model = SaleEvent
        fields = [
            "id",
            "pos_sale_id",
            "cashier",
            "sold_at",
            "totals",
            "status",
            "payload",
            "ingested_at",
        ]
        read_only_fields = fields


class SaleLineSerializer(serializers.Serializer):
    """One line in an incoming POS sale."""

    pos_code = serializers.CharField()
    qty = serializers.DecimalField(max_digits=12, decimal_places=3, default=1)
    modifiers = serializers.ListField(required=False, default=list)
    price = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )


class SaleEventIngestSerializer(serializers.Serializer):
    """Incoming POS sale payload (push or pull)."""

    pos_sale_id = serializers.CharField()
    sold_at = serializers.DateTimeField()
    cashier = serializers.CharField(required=False, allow_blank=True, default="")
    table_ref = serializers.CharField(required=False, allow_blank=True, default="")
    lines = SaleLineSerializer(many=True)
    totals = serializers.DictField(required=False, default=dict)

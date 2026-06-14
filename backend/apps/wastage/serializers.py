"""Serializers for wastage entries."""

from rest_framework import serializers

from apps.wastage.models import WastageEntry


class WastageEntrySerializer(serializers.ModelSerializer):
    """Read shape for a wastage entry."""

    reason_label = serializers.CharField(source="reason_code.label", read_only=True)
    logged_by_name = serializers.CharField(source="logged_by.full_name", read_only=True)

    class Meta:
        model = WastageEntry
        fields = [
            "id",
            "entry_type",
            "order",
            "product",
            "location",
            "qty",
            "reason_code",
            "reason_label",
            "note",
            "value",
            "logged_by",
            "logged_by_name",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "value", "status", "logged_by", "created_at"]


class WastageCreateSerializer(serializers.Serializer):
    """Payload to log a breakage or spoilage event."""

    entry_type = serializers.ChoiceField(
        choices=[WastageEntry.EntryType.BREAKAGE, WastageEntry.EntryType.SPOILAGE]
    )
    product = serializers.UUIDField()
    location = serializers.UUIDField()
    qty = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=0)
    reason_code = serializers.UUIDField()
    note = serializers.CharField(required=False, allow_blank=True, default="")

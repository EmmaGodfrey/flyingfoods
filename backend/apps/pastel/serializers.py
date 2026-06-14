"""Serializers for the Pastel integration API."""

from rest_framework import serializers

from apps.core.models import OutboxRecord
from apps.pastel.models import PastelSyncLog, ReconciliationLine, ReconciliationRun


class OutboxRecordSerializer(serializers.ModelSerializer):
    """Read-only view of an OutboxRecord for the sync-log and resend endpoints."""

    class Meta:
        model = OutboxRecord
        fields = [
            "id",
            "entity_type",
            "entity_id",
            "status",
            "attempts",
            "next_attempt_at",
            "created_at",
        ]


class PastelSyncLogSerializer(serializers.ModelSerializer):
    """One attempt to push an OutboxRecord to Pastel."""

    outbox = OutboxRecordSerializer(read_only=True)

    class Meta:
        model = PastelSyncLog
        fields = [
            "id",
            "outbox",
            "attempted_at",
            "status",
            "request_payload",
            "response",
            "created_at",
        ]


class ReconciliationLineSerializer(serializers.ModelSerializer):
    """One product/location pair in a reconciliation run."""

    product_code = serializers.CharField(source="product.code", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    location_name = serializers.CharField(source="location.name", read_only=True)

    class Meta:
        model = ReconciliationLine
        fields = [
            "id",
            "product",
            "product_code",
            "product_name",
            "location",
            "location_name",
            "our_on_hand",
            "pastel_on_hand",
            "divergence",
        ]


class ReconciliationRunSerializer(serializers.ModelSerializer):
    """A reconciliation run with all its divergent lines nested."""

    lines = serializers.SerializerMethodField()

    class Meta:
        model = ReconciliationRun
        fields = ["id", "run_date", "created_by", "created_at", "lines"]

    def get_lines(self, obj: ReconciliationRun) -> list:
        """Return all lines where divergence is non-zero."""
        divergent = obj.lines.exclude(divergence=0).select_related(
            "product", "location"
        )
        return ReconciliationLineSerializer(divergent, many=True).data

"""Serializers for core configuration and approval models."""

from rest_framework import serializers

from apps.core.models import Approval, IntegrationSettings, ReasonCode, ThresholdConfig


class ReasonCodeSerializer(serializers.ModelSerializer):
    """Serializer for ReasonCode configuration records."""

    class Meta:
        model = ReasonCode
        fields = ["id", "category", "label", "is_active"]


class ThresholdConfigSerializer(serializers.ModelSerializer):
    """Serializer for monetary approval thresholds."""

    class Meta:
        model = ThresholdConfig
        fields = ["id", "scope", "amount", "is_active"]


class IntegrationSettingsSerializer(serializers.ModelSerializer):
    """Serializer for integration key-value settings."""

    class Meta:
        model = IntegrationSettings
        fields = ["id", "key", "value"]


class ApprovalSerializer(serializers.ModelSerializer):
    """Serializer for Approval records, with a human label and value for the
    document under review so a manager can decide without leaving the queue."""

    requested_by_name = serializers.CharField(
        source="requested_by.full_name", read_only=True
    )
    subject_type = serializers.StringRelatedField(read_only=True)
    subject_label = serializers.SerializerMethodField()
    subject_value = serializers.SerializerMethodField()

    class Meta:
        model = Approval
        fields = [
            "id",
            "scope",
            "status",
            "threshold_snapshot",
            "requested_by",
            "requested_by_name",
            "decided_by",
            "reason",
            "decided_at",
            "subject_id",
            "subject_type",
            "subject_label",
            "subject_value",
            "created_at",
        ]
        read_only_fields = fields

    def get_subject_label(self, obj: Approval) -> str:
        """Friendly description of the document under review.

        Detected by attribute so core need not import the feature models:
        wastage shows the product and quantity, transfers/issues show the
        locations, budgets show their line count; anything else falls back to
        the model's own string form.
        """
        subject = obj.subject
        if subject is None:
            return ""
        if hasattr(subject, "entry_type") and hasattr(subject, "product"):
            qty = str(subject.qty).rstrip("0").rstrip(".") if subject.qty is not None else ""
            return f"{str(subject.entry_type).title()} · {subject.product.name} ×{qty}"
        if hasattr(subject, "source") and hasattr(subject, "destination"):
            return f"{subject.source.name} → {subject.destination.name}"
        if hasattr(subject, "total_estimated"):
            count = subject.lines.count()
            return f"Purchase budget · {count} item{'s' if count != 1 else ''}"
        return str(subject)

    def get_subject_value(self, obj: Approval) -> str | None:
        """Monetary value of the document, read from whichever total it carries."""
        subject = obj.subject
        if subject is None:
            return None
        for attr in ("total_estimated", "total_value", "value", "amount"):
            val = getattr(subject, attr, None)
            if val is not None:
                return str(val)
        return None

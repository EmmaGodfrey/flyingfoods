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
    """Serializer for Approval records including requester name and subject label."""

    requested_by_name = serializers.CharField(
        source="requested_by.full_name", read_only=True
    )
    subject_type = serializers.StringRelatedField(read_only=True)

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
            "created_at",
        ]
        read_only_fields = fields

"""Serializers for the notifications resource."""

from rest_framework import serializers

from apps.notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification list and read-receipt action."""

    subject_type = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id",
            "kind",
            "subject_type",
            "subject_id",
            "body",
            "read_at",
            "created_at",
        ]
        read_only_fields = fields

"""Views for the notifications endpoints.

GET  /api/notifications/           — list own notifications, newest first.
POST /api/notifications/{pk}/read/ — mark a single notification as read.
"""

import uuid

from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationSerializer


class NotificationListView(generics.ListAPIView):
    """Return the requesting user's notifications, newest first.

    Optional query param:
      ?unread=true  — only return notifications where read_at is null.
    """

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter to the current user's notifications; honour ?unread=true."""
        qs = Notification.objects.filter(recipient=self.request.user).order_by("-created_at")
        if self.request.query_params.get("unread", "").lower() == "true":
            qs = qs.filter(read_at__isnull=True)
        return qs


class NotificationReadView(APIView):
    """POST /api/notifications/{pk}/read/ — mark own notification as read."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request, pk: uuid.UUID) -> Response:
        """Set read_at to now if not already set; ignore if already read.

        Args:
            request: The incoming HTTP request.
            pk: UUID primary key of the Notification to mark as read.

        Returns:
            Serialized notification with updated read_at.
        """
        notification = Notification.objects.filter(
            pk=pk, recipient=request.user
        ).first()
        if notification is None:
            return Response(
                {"detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if notification.read_at is None:
            notification.read_at = timezone.now()
            notification.save(update_fields=["read_at", "updated_at"])
        serializer = NotificationSerializer(notification)
        return Response(serializer.data)

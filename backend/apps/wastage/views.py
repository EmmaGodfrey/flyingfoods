"""Wastage logging endpoints."""

from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.request import Request
from rest_framework.response import Response

from apps.core.models import ReasonCode
from apps.users.permissions import IsKitchenStaff
from apps.wastage.models import WastageEntry
from apps.wastage.serializers import WastageCreateSerializer, WastageEntrySerializer
from apps.wastage.services import create_wastage


class WastageListCreateView(generics.ListCreateAPIView):
    """GET/POST /api/wastage/ — log breakage/spoilage or list entries."""

    serializer_class = WastageEntrySerializer
    permission_classes = [IsKitchenStaff]
    filterset_fields = ["entry_type", "status", "location", "product"]

    def get_queryset(self):
        return WastageEntry.objects.select_related("reason_code", "logged_by").order_by("-created_at")

    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer = WastageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        reason = get_object_or_404(ReasonCode, pk=data["reason_code"])
        entry = create_wastage(
            entry_type=data["entry_type"],
            product_id=data["product"],
            location_id=data["location"],
            qty=data["qty"],
            reason_code=reason,
            logged_by=request.user,
            note=data["note"],
        )
        return Response(WastageEntrySerializer(entry).data, status=201)

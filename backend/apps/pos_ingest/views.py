"""POS ingestion endpoints: push intake, listing, and replay."""

from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.pos_ingest.models import SaleEvent
from apps.pos_ingest.serializers import SaleEventIngestSerializer, SaleEventSerializer
from apps.pos_ingest.services import ingest_sale_event, replay_sale_event
from apps.users.permissions import IsAdmin


class SaleEventIngestView(APIView):
    """POST /api/pos/sale-events/ — push or pull intake, idempotent on sale ID."""

    def post(self, request: Request) -> Response:
        serializer = SaleEventIngestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = ingest_sale_event(request.data)
        code = (
            status.HTTP_202_ACCEPTED
            if event.status == SaleEvent.Status.FLAGGED_UNKNOWN_ITEM
            else status.HTTP_200_OK
        )
        return Response(SaleEventSerializer(event).data, status=code)


class SaleEventListView(generics.ListAPIView):
    """GET /api/pos/sale-events/ — raw events for the Administrator."""

    serializer_class = SaleEventSerializer
    permission_classes = [IsAdmin]
    filterset_fields = ["status"]

    def get_queryset(self):
        return SaleEvent.objects.all().order_by("-ingested_at")


class SaleEventReplayView(APIView):
    """POST /api/pos/sale-events/{id}/replay/ — re-run ingestion side effects."""

    permission_classes = [IsAdmin]

    def post(self, request: Request, pk) -> Response:
        event = get_object_or_404(SaleEvent, pk=pk)
        replay_sale_event(event=event, replayed_by=request.user)
        return Response(SaleEventSerializer(event).data)

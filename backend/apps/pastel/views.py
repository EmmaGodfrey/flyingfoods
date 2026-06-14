"""Views for the Pastel integration API.

All views require IsAdmin unless noted. Mounted at /api/pastel/ by config/urls.py.

Endpoints:
  GET  /api/pastel/sync-log/            — list PastelSyncLog (IsAdmin)
  POST /api/pastel/outbox/{id}/resend/  — manually resend a failed record (IsAdmin)
  GET  /api/pastel/reconciliation/      — latest run + divergent lines (IsAdmin|IsManager)
"""

from django.utils import timezone
from rest_framework.exceptions import NotFound
from rest_framework.generics import ListAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.exceptions import DomainError
from apps.core.models import OutboxRecord


class AlreadySentError(DomainError):
    """Raised when resending an OutboxRecord that already reached Pastel."""

    status_code = 400
    default_code = "ALREADY_SENT"
    default_detail = "This record has already been sent."
from apps.pastel.models import PastelSyncLog, ReconciliationRun
from apps.pastel.serializers import (
    OutboxRecordSerializer,
    PastelSyncLogSerializer,
    ReconciliationRunSerializer,
)
from apps.users.permissions import IsAdmin, IsManager


class SyncLogListView(ListAPIView):
    """List PastelSyncLog entries, newest first.

    Supports optional query params:
      ?status=SUCCESS|FAILED
      ?date=YYYY-MM-DD   (filters by attempted_at date)
      ?entity=<entity_type>
    """

    permission_classes = [IsAdmin]
    serializer_class = PastelSyncLogSerializer

    def get_queryset(self):
        """Return filtered sync logs, newest first."""
        qs = PastelSyncLog.objects.select_related(
            "outbox"
        ).order_by("-attempted_at")

        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)

        date_param = self.request.query_params.get("date")
        if date_param:
            qs = qs.filter(attempted_at__date=date_param)

        entity_param = self.request.query_params.get("entity")
        if entity_param:
            qs = qs.filter(outbox__entity_type=entity_param)

        return qs


class ResendOutboxView(APIView):
    """Reset a failed/abandoned OutboxRecord and push it to Pastel immediately.

    Resets status to PENDING and next_attempt_at to now, then calls
    send_to_pastel once synchronously. Returns the updated OutboxRecord.
    """

    permission_classes = [IsAdmin]

    def post(self, request: Request, pk: str) -> Response:
        """Resend a specific OutboxRecord.

        Args:
            request: The incoming request.
            pk: UUID of the OutboxRecord to resend.

        Returns:
            200 with updated OutboxRecord data on success,
            404 if not found,
            400 if the record is already SENT.
        """
        from apps.pastel.adapter import send_to_pastel

        record = OutboxRecord.objects.filter(pk=pk).first()
        if record is None:
            raise NotFound("Outbox record not found.")
        if record.status == OutboxRecord.Status.SENT:
            raise AlreadySentError()

        record.status = OutboxRecord.Status.PENDING
        record.next_attempt_at = timezone.now()
        record.save(update_fields=["status", "next_attempt_at", "updated_at"])

        if send_to_pastel(record):
            record.status = OutboxRecord.Status.SENT
        else:
            record.status = OutboxRecord.Status.FAILED
            record.attempts += 1
        record.save(update_fields=["status", "attempts", "updated_at"])

        record.refresh_from_db()
        return Response(OutboxRecordSerializer(record).data)


class ReconciliationView(APIView):
    """Return the latest ReconciliationRun with divergent lines.

    Accepts an optional ?run= query param to return a specific run by id.
    Passing ?trigger=1 creates a fresh run synchronously and returns it.

    Roles: IsAdmin or IsManager.
    """

    permission_classes = [IsAdmin | IsManager]

    def get(self, request: Request) -> Response:
        """Return the latest (or specified) reconciliation run.

        Args:
            request: The incoming request.

        Returns:
            200 with ReconciliationRun data, or 404 if no run exists yet.
        """
        from apps.pastel.tasks import run_reconciliation_now

        if request.query_params.get("trigger"):
            run = ReconciliationRun.objects.get(pk=run_reconciliation_now())
            return Response(ReconciliationRunSerializer(run).data)

        run_pk = request.query_params.get("run")
        if run_pk:
            run = ReconciliationRun.objects.filter(pk=run_pk).first()
            if run is None:
                raise NotFound("Reconciliation run not found.")
        else:
            run = ReconciliationRun.objects.order_by("-run_date", "-created_at").first()
            if run is None:
                raise NotFound("No reconciliation runs found.")

        return Response(ReconciliationRunSerializer(run).data)

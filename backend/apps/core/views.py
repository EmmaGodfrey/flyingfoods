"""Views for core configuration resources and the approval queue.

Thin views: validation in serializers, business logic in services.py.
"""

import uuid
from typing import Any

from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.filters import ApprovalFilter, ReasonCodeFilter, ThresholdConfigFilter
from apps.core.models import Approval, IntegrationSettings, ReasonCode, ThresholdConfig
from apps.core.serializers import (
    ApprovalSerializer,
    IntegrationSettingsSerializer,
    ReasonCodeSerializer,
    ThresholdConfigSerializer,
)
from apps.core.services import decide_approval
from apps.users.permissions import IsAdmin, IsManager


class HealthView(APIView):
    """Unauthenticated liveness endpoint for containers and load balancers."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        """Confirm that the Django application is serving requests."""
        return Response({"status": "ok"})


# ---------------------------------------------------------------------------
# ReasonCode
# ---------------------------------------------------------------------------


class ReasonCodeListCreateView(generics.ListCreateAPIView):
    """GET /reason-codes/ — any authenticated; POST — ADMIN only."""

    serializer_class = ReasonCodeSerializer
    filterset_class = ReasonCodeFilter
    queryset = ReasonCode.objects.order_by("category", "label")

    def get_permissions(self) -> list[Any]:
        """Any authenticated user may list; only ADMIN may create."""
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return [IsAdmin()]


class ReasonCodeDetailView(generics.RetrieveUpdateAPIView):
    """GET /reason-codes/{pk}/ — any authenticated; PATCH — ADMIN only."""

    serializer_class = ReasonCodeSerializer
    queryset = ReasonCode.objects.all()
    http_method_names = ["get", "patch", "head", "options"]

    def get_permissions(self) -> list[Any]:
        """Any authenticated user may retrieve; only ADMIN may update."""
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return [IsAdmin()]


# ---------------------------------------------------------------------------
# ThresholdConfig
# ---------------------------------------------------------------------------


class ThresholdConfigListCreateView(generics.ListCreateAPIView):
    """GET /thresholds/ — any authenticated; POST — ADMIN only."""

    serializer_class = ThresholdConfigSerializer
    filterset_class = ThresholdConfigFilter
    queryset = ThresholdConfig.objects.order_by("scope")

    def get_permissions(self) -> list[Any]:
        """Any authenticated user may list; only ADMIN may create."""
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return [IsAdmin()]


class ThresholdConfigDetailView(generics.RetrieveUpdateAPIView):
    """GET /thresholds/{pk}/ — any authenticated; PATCH — ADMIN only."""

    serializer_class = ThresholdConfigSerializer
    queryset = ThresholdConfig.objects.all()
    http_method_names = ["get", "patch", "head", "options"]

    def get_permissions(self) -> list[Any]:
        """Any authenticated user may retrieve; only ADMIN may update."""
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return [IsAdmin()]


# ---------------------------------------------------------------------------
# IntegrationSettings
# ---------------------------------------------------------------------------


class IntegrationSettingsListView(generics.ListAPIView):
    """GET /integration-settings/ — list all; PUT — upsert one key (ADMIN only)."""

    serializer_class = IntegrationSettingsSerializer
    permission_classes = [IsAdmin]
    queryset = IntegrationSettings.objects.order_by("key")
    pagination_class = None

    def put(self, request: Request) -> Response:
        """Create or update the IntegrationSettings row for the given key.

        Args:
            request: HTTP request with JSON body containing `key` and `value`.

        Returns:
            Serialized IntegrationSettings row with HTTP 200.
        """
        serializer = IntegrationSettingsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        key = serializer.validated_data["key"]
        value = serializer.validated_data["value"]

        obj, _ = IntegrationSettings.objects.update_or_create(
            key=key,
            defaults={"value": value},
        )
        return Response(IntegrationSettingsSerializer(obj).data)


# ---------------------------------------------------------------------------
# Integration health
# ---------------------------------------------------------------------------


class IntegrationHealthView(APIView):
    """GET /integration-health/ — live failure counts from POS and Pastel apps.

    Each sub-system is queried lazily so this view stays functional even when
    those apps have not been migrated yet.
    """

    permission_classes = [IsAdmin]

    def get(self, request: Request) -> Response:
        """Return a health card per integration for the admin panel.

        Returns:
            A JSON list of objects with ``key``, ``label``, ``status``,
            ``detail``, ``failure_count``, and ``last_run_at``.
        """
        pos = self._pos_health()
        pastel = self._pastel_health()

        pos_failures = pos["flagged_count"] + pos["failed_count"]
        if pos["failed_count"]:
            pos_status = "FAILED"
        elif pos["flagged_count"]:
            pos_status = "DEGRADED"
        else:
            pos_status = "OK"

        pastel_status = "FAILED" if pastel["failed_count"] else "OK"

        cards = [
            {
                "key": "pos",
                "label": "POS Ingestion",
                "status": pos_status,
                "detail": f"{pos['flagged_count']} flagged, {pos['failed_count']} failed",
                "failure_count": pos_failures,
                "last_run_at": None,
            },
            {
                "key": "pastel",
                "label": "Pastel Sync",
                "status": pastel_status,
                "detail": f"{pastel['failed_count']} failed in outbox",
                "failure_count": pastel["failed_count"],
                "last_run_at": None,
            },
        ]
        return Response(cards)

    def _pos_health(self) -> dict:
        """Return POS ingest failure counts.

        Returns zero counts with an error note if the pos_ingest app is not
        yet available.
        """
        try:
            from apps.pos_ingest.models import SaleEvent  # type: ignore[import]

            flagged = SaleEvent.objects.filter(status="FLAGGED_UNKNOWN_ITEM").count()
            failed = SaleEvent.objects.filter(status="FAILED").count()
            return {"flagged_count": flagged, "failed_count": failed}
        except ImportError:
            return {"flagged_count": 0, "failed_count": 0, "note": "pos_ingest app not available"}

    def _pastel_health(self) -> dict:
        """Return Pastel outbox failure counts.

        Returns zero counts with an error note if the pastel app is not yet
        available.
        """
        try:
            from apps.core.models import OutboxRecord

            failed = OutboxRecord.objects.filter(status="FAILED").count()
            return {"failed_count": failed}
        except Exception:
            return {"failed_count": 0, "note": "outbox unavailable"}


# ---------------------------------------------------------------------------
# Approvals
# ---------------------------------------------------------------------------


class ApprovalListView(generics.ListAPIView):
    """GET /approvals/ — Manager+ only, newest first."""

    serializer_class = ApprovalSerializer
    permission_classes = [IsManager]
    filterset_class = ApprovalFilter

    def get_queryset(self):
        """Return approvals with users pre-fetched, newest first."""
        return (
            Approval.objects.select_related("requested_by", "decided_by", "subject_type")
            .order_by("-created_at")
        )


class ApprovalDecideView(APIView):
    """POST /approvals/{pk}/approve|reject|investigate/ — Manager+ only."""

    permission_classes = [IsManager]

    def _decide(self, request: Request, pk: uuid.UUID, decision: str) -> Response:
        """Resolve an approval with the given decision.

        Args:
            request: HTTP request; body may contain ``{"reason": "..."}``.
            pk: UUID of the Approval to decide.
            decision: One of Approval.Status APPROVED / REJECTED / INVESTIGATION.

        Returns:
            Serialized updated Approval, or 404 if not found.
        """
        approval = Approval.objects.filter(pk=pk).first()
        if approval is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        reason = request.data.get("reason", "")
        updated = decide_approval(
            approval=approval,
            decided_by=request.user,
            decision=decision,
            reason=reason,
        )
        return Response(ApprovalSerializer(updated).data)

    def post(self, request: Request, pk: uuid.UUID, action: str) -> Response:
        """Dispatch to the correct decision based on URL action segment.

        Args:
            request: The incoming HTTP request.
            pk: UUID of the target Approval.
            action: One of ``approve``, ``reject``, ``investigate``.

        Returns:
            Serialized Approval or 400 for unknown action.
        """
        decision_map = {
            "approve": Approval.Status.APPROVED,
            "reject": Approval.Status.REJECTED,
            "investigate": Approval.Status.INVESTIGATION,
        }
        decision = decision_map.get(action)
        if decision is None:
            return Response(
                {"detail": f"Unknown action: {action}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return self._decide(request, pk, decision)


class ApprovalApproveView(ApprovalDecideView):
    """POST /approvals/{pk}/approve/"""

    def post(self, request: Request, pk: uuid.UUID) -> Response:  # type: ignore[override]
        """Approve the target approval record."""
        return self._decide(request, pk, Approval.Status.APPROVED)


class ApprovalRejectView(ApprovalDecideView):
    """POST /approvals/{pk}/reject/"""

    def post(self, request: Request, pk: uuid.UUID) -> Response:  # type: ignore[override]
        """Reject the target approval record."""
        return self._decide(request, pk, Approval.Status.REJECTED)


class ApprovalInvestigateView(ApprovalDecideView):
    """POST /approvals/{pk}/investigate/"""

    def post(self, request: Request, pk: uuid.UUID) -> Response:  # type: ignore[override]
        """Place the target approval under investigation."""
        return self._decide(request, pk, Approval.Status.INVESTIGATION)

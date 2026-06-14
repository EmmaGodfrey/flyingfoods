"""Procurement views: thin controllers delegating all logic to services."""

from decimal import Decimal

from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.masterdata.models import Supplier
from apps.procurement.models import InvoiceMatch, PurchaseBudget, PurchaseOrder
from apps.procurement.selectors import supplier_history
from apps.procurement.serializers import (
    GRNCreateSerializer,
    GRNSerializer,
    InvoiceMatchSerializer,
    PurchaseBudgetCreateSerializer,
    PurchaseBudgetSerializer,
    PurchaseOrderCreateSerializer,
    PurchaseOrderSerializer,
    SupplierInvoiceCreateSerializer,
    SupplierInvoiceSerializer,
)
from apps.procurement.services import (
    create_po,
    dispute_match,
    escalate_match,
    match_invoice,
    post_grn,
    resolve_match,
    send_po,
    submit_budget,
)
from apps.users.permissions import IsManager, IsProcurementStaff, IsReceivingOfficer


# ---------------------------------------------------------------------------
# Budget views
# ---------------------------------------------------------------------------


class BudgetListView(generics.ListAPIView):
    """GET /budgets/ — list all purchase budgets (procurement staff only)."""

    serializer_class = PurchaseBudgetSerializer
    permission_classes = [IsProcurementStaff]

    def get_queryset(self):
        """Return all budgets ordered newest first."""
        return PurchaseBudget.objects.prefetch_related("lines").order_by("-created_at")


class BudgetCreateView(generics.CreateAPIView):
    """POST /budgets/ — create a draft purchase budget (any authenticated user)."""

    serializer_class = PurchaseBudgetCreateSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request: Request, *args, **kwargs) -> Response:
        """Create the budget and return 201 with the full representation."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        budget = serializer.save()
        out = PurchaseBudgetSerializer(budget, context={"request": request})
        return Response(out.data, status=status.HTTP_201_CREATED)


class BudgetSubmitView(APIView):
    """POST /budgets/{id}/submit/ — submit a budget for manager approval."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request, pk: str) -> Response:
        """Submit the budget; returns the updated budget representation."""
        budget = get_object_or_404(PurchaseBudget, pk=pk)
        submit_budget(budget=budget, user=request.user)
        out = PurchaseBudgetSerializer(budget, context={"request": request})
        return Response(out.data, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Purchase Order views
# ---------------------------------------------------------------------------


class PurchaseOrderListView(generics.ListAPIView):
    """GET /purchase-orders/ — list all purchase orders."""

    serializer_class = PurchaseOrderSerializer
    permission_classes = [IsProcurementStaff]

    def get_queryset(self):
        """Return all POs with related lines."""
        return PurchaseOrder.objects.select_related("budget", "supplier").prefetch_related(
            "lines"
        ).order_by("-created_at")


class PurchaseOrderCreateView(APIView):
    """POST /purchase-orders/ — create a PO against an approved budget."""

    permission_classes = [IsProcurementStaff]

    def post(self, request: Request) -> Response:
        """Validate the payload and delegate creation to the service layer."""
        serializer = PurchaseOrderCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        budget = get_object_or_404(PurchaseBudget, pk=data["budget"].pk)
        supplier = get_object_or_404(Supplier, pk=data["supplier"].pk)

        lines = [
            {
                "product_id": line["product"].pk,
                "qty": line["qty"],
                "unit_price": line["unit_price"],
            }
            for line in data["lines"]
        ]

        po = create_po(budget=budget, supplier=supplier, lines=lines, user=request.user)
        out = PurchaseOrderSerializer(po, context={"request": request})
        return Response(out.data, status=status.HTTP_201_CREATED)


class PurchaseOrderSendView(APIView):
    """POST /purchase-orders/{id}/send/ — send PO to supplier via email or flag for manual contact."""

    permission_classes = [IsProcurementStaff]

    def post(self, request: Request, pk: str) -> Response:
        """Send the PO and return the updated PO representation."""
        po = get_object_or_404(PurchaseOrder, pk=pk)
        send_po(po=po, user=request.user)
        out = PurchaseOrderSerializer(po, context={"request": request})
        return Response(out.data, status=status.HTTP_200_OK)


class PurchaseOrderPdfView(APIView):
    """GET /purchase-orders/{id}/pdf/ — stream the stored PO PDF."""

    permission_classes = [IsProcurementStaff]

    def get(self, request: Request, pk: str) -> Response:
        """Return the stored PDF file or 404 if no PDF has been generated yet."""
        po = get_object_or_404(PurchaseOrder, pk=pk)
        if not po.pdf_file:
            return Response(
                {"detail": "PDF not available for this purchase order."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return FileResponse(po.pdf_file.open("rb"), content_type="application/pdf")


# ---------------------------------------------------------------------------
# GRN views
# ---------------------------------------------------------------------------


class GRNCreateView(APIView):
    """POST /purchase-orders/{id}/grns/ — post a Goods Received Note."""

    permission_classes = [IsReceivingOfficer]

    def post(self, request: Request, pk: str) -> Response:
        """Validate GRN lines, post movements, and return the created GRN."""
        po = get_object_or_404(PurchaseOrder, pk=pk)
        serializer = GRNCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        lines_data = [
            {
                "po_line_id": line["po_line"].pk,
                "qty_received": line["qty_received"],
                "unit_cost": line["unit_cost"],
                "condition": line.get("condition", ""),
                "variance_reason_id": line.get("variance_reason_id"),
            }
            for line in serializer.validated_data["lines"]
        ]

        grn = post_grn(po=po, lines_data=lines_data, received_by=request.user)
        out = GRNSerializer(grn, context={"request": request})
        return Response(out.data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Invoice views
# ---------------------------------------------------------------------------


class InvoiceCreateView(APIView):
    """POST /purchase-orders/{id}/invoices/ — record a supplier invoice and 3-way match."""

    permission_classes = [IsProcurementStaff]

    def post(self, request: Request, pk: str) -> Response:
        """Create the invoice, run the match, and return the match result."""
        po = get_object_or_404(PurchaseOrder, pk=pk)
        serializer = SupplierInvoiceCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        invoice, match = match_invoice(
            po=po,
            invoice_ref=data["invoice_ref"],
            amount=Decimal(str(data["amount"])),
            user=request.user,
            file=data.get("file"),
        )
        out = InvoiceMatchSerializer(match, context={"request": request})
        return Response(out.data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Invoice match action views
# ---------------------------------------------------------------------------


class InvoiceMatchResolveView(APIView):
    """POST /invoice-matches/{id}/resolve/ — mark an invoice match as resolved."""

    permission_classes = [IsProcurementStaff]

    def post(self, request: Request, pk: str) -> Response:
        """Resolve the match and return the updated representation."""
        match = get_object_or_404(InvoiceMatch, pk=pk)
        updated = resolve_match(match=match, user=request.user)
        out = InvoiceMatchSerializer(updated, context={"request": request})
        return Response(out.data, status=status.HTTP_200_OK)


class InvoiceMatchDisputeView(APIView):
    """POST /invoice-matches/{id}/dispute/ — flag an invoice match as disputed."""

    permission_classes = [IsProcurementStaff]

    def post(self, request: Request, pk: str) -> Response:
        """Dispute the match and return the updated representation."""
        match = get_object_or_404(InvoiceMatch, pk=pk)
        updated = dispute_match(match=match, user=request.user)
        out = InvoiceMatchSerializer(updated, context={"request": request})
        return Response(out.data, status=status.HTTP_200_OK)


class InvoiceMatchEscalateView(APIView):
    """POST /invoice-matches/{id}/escalate/ — escalate an invoice match for senior review."""

    permission_classes = [IsProcurementStaff]

    def post(self, request: Request, pk: str) -> Response:
        """Escalate the match and return the updated representation."""
        match = get_object_or_404(InvoiceMatch, pk=pk)
        updated = escalate_match(match=match, user=request.user)
        out = InvoiceMatchSerializer(updated, context={"request": request})
        return Response(out.data, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Supplier history view
# ---------------------------------------------------------------------------


class SupplierHistoryView(APIView):
    """GET /supplier-history/{id}/ — return full procurement history for a supplier."""

    permission_classes = [IsProcurementStaff]

    def get(self, request: Request, pk: str) -> Response:
        """Return POs, GRNs, and invoices for the given supplier."""
        supplier = get_object_or_404(Supplier, pk=pk)
        history = supplier_history(supplier=supplier)

        pos_data = PurchaseOrderSerializer(
            history["pos"], many=True, context={"request": request}
        ).data
        grns_data = GRNSerializer(
            history["grns"], many=True, context={"request": request}
        ).data
        invoices_data = SupplierInvoiceSerializer(
            history["invoices"], many=True, context={"request": request}
        ).data

        return Response(
            {
                "supplier_id": history["supplier_id"],
                "purchase_orders": pos_data,
                "grns": grns_data,
                "invoices": invoices_data,
            },
            status=status.HTTP_200_OK,
        )

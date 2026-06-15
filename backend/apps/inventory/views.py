"""Inventory API views: balances, movements, issues, transfers, stock-takes."""

from typing import Any

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.idempotency import idempotent
from apps.inventory.filters import StockBalanceFilter, StockMovementFilter
from apps.inventory.models import (
    IssueNote,
    StockBalance,
    StockMovement,
    StockTake,
    StockTakeLine,
    Transfer,
    TransferLine,
)
from apps.inventory.serializers import (
    IssueNoteCreateSerializer,
    IssueNoteSerializer,
    StockBalanceSerializer,
    StockMovementSerializer,
    StockTakeCountsSerializer,
    StockTakeSerializer,
    TransferCreateSerializer,
    TransferSerializer,
)
from apps.inventory.services import (
    create_issue_note,
    open_stock_take,
    post_issue_note,
    post_stock_take,
    post_transfer,
)
from apps.masterdata.models import Location
from apps.users.permissions import IsIssuer, IsStockViewer, IsStorekeeper


# ---------------------------------------------------------------------------
# Stock balances
# ---------------------------------------------------------------------------


class StockBalanceListView(generics.ListAPIView):
    """GET /stock/balances/ — paginated, filtered on-hand balances."""

    permission_classes = [IsStockViewer]
    serializer_class = StockBalanceSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = StockBalanceFilter

    def get_queryset(self):
        """Return all balances with product and location pre-fetched."""
        return (
            StockBalance.objects.select_related("product", "location")
            .order_by("product__name", "location__name")
        )


# ---------------------------------------------------------------------------
# Stock movements (ledger — read-only)
# ---------------------------------------------------------------------------


class StockMovementListView(generics.ListAPIView):
    """GET /stock/movements/ — append-only ledger, read-only."""

    permission_classes = [IsStockViewer]
    serializer_class = StockMovementSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = StockMovementFilter

    def get_queryset(self):
        """Return all movements with related objects pre-fetched."""
        return (
            StockMovement.objects.select_related("product", "location", "posted_by")
            .order_by("-posted_at")
        )


# ---------------------------------------------------------------------------
# Issue notes
# ---------------------------------------------------------------------------


class IssueNoteCreateView(generics.ListCreateAPIView):
    """GET /issues/ — list issue notes. POST /issues/ — create a draft issue note."""

    serializer_class = IssueNoteSerializer

    def get_permissions(self) -> list[Any]:
        """Stock viewers may list; only issuers may create."""
        if self.request.method == "GET":
            return [IsStockViewer()]
        return [IsIssuer()]

    def get_queryset(self):
        """Return issue notes with related locations and lines, newest first."""
        return (
            IssueNote.objects.select_related("source", "destination")
            .prefetch_related("lines")
            .order_by("-created_at")
        )

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Validate input, resolve locations, delegate to service, return serialized note."""
        input_serializer = IssueNoteCreateSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        data = input_serializer.validated_data

        source = generics.get_object_or_404(Location, pk=data["source"])
        destination = generics.get_object_or_404(Location, pk=data["destination"])
        lines = [(line["product"], line["qty"]) for line in data["lines"]]

        note = create_issue_note(
            source=source,
            destination=destination,
            requested_by=request.user,
            lines=lines,
            off_schedule_reason_id=data.get("off_schedule_reason"),
        )
        note_with_lines = IssueNote.objects.prefetch_related("lines").get(pk=note.pk)
        return Response(
            IssueNoteSerializer(note_with_lines).data,
            status=status.HTTP_201_CREATED,
        )


class IssueNotePostView(APIView):
    """POST /issues/{id}/post/ — post a draft issue note, moving stock."""

    permission_classes = [IsIssuer]

    @idempotent
    def post(self, request: Request, pk: Any, *args: Any, **kwargs: Any) -> Response:
        """Post the issue note identified by pk; honour override flag."""
        note = generics.get_object_or_404(IssueNote, pk=pk)
        allow_negative = bool(request.data.get("override"))
        posted = post_issue_note(
            issue_note=note,
            posted_by=request.user,
            allow_negative=allow_negative,
        )
        posted_with_lines = IssueNote.objects.prefetch_related("lines").get(pk=posted.pk)
        return Response(IssueNoteSerializer(posted_with_lines).data)


# ---------------------------------------------------------------------------
# Transfers
# ---------------------------------------------------------------------------


class TransferCreateView(generics.ListCreateAPIView):
    """GET /transfers/ — list transfers. POST /transfers/ — create a draft transfer."""

    serializer_class = TransferSerializer

    def get_permissions(self) -> list[Any]:
        """Stock viewers may list; only issuers may create."""
        if self.request.method == "GET":
            return [IsStockViewer()]
        return [IsIssuer()]

    def get_queryset(self):
        """Return transfers with related locations and lines, newest first."""
        return (
            Transfer.objects.select_related("source", "destination")
            .prefetch_related("lines")
            .order_by("-created_at")
        )

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Validate input, create Transfer + TransferLines (DRAFT), return serialized."""
        input_serializer = TransferCreateSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        data = input_serializer.validated_data

        source = generics.get_object_or_404(Location, pk=data["source"])
        destination = generics.get_object_or_404(Location, pk=data["destination"])

        transfer = Transfer.objects.create(
            source=source,
            destination=destination,
            requested_by=request.user,
            status=Transfer.Status.DRAFT,
        )
        TransferLine.objects.bulk_create(
            [
                TransferLine(
                    transfer=transfer,
                    product_id=line["product"],
                    qty=line["qty"],
                )
                for line in data["lines"]
            ]
        )
        transfer_with_lines = Transfer.objects.prefetch_related("lines").get(pk=transfer.pk)
        return Response(
            TransferSerializer(transfer_with_lines).data,
            status=status.HTTP_201_CREATED,
        )


class TransferPostView(APIView):
    """POST /transfers/{id}/post/ — post a draft transfer, routing through approval if needed."""

    permission_classes = [IsIssuer]

    @idempotent
    def post(self, request: Request, pk: Any, *args: Any, **kwargs: Any) -> Response:
        """Post the transfer identified by pk."""
        transfer = generics.get_object_or_404(Transfer, pk=pk)
        posted = post_transfer(transfer=transfer, posted_by=request.user)
        posted_with_lines = Transfer.objects.prefetch_related("lines").get(pk=posted.pk)
        return Response(TransferSerializer(posted_with_lines).data)


# ---------------------------------------------------------------------------
# Stock takes
# ---------------------------------------------------------------------------


class StockTakeCreateView(generics.CreateAPIView):
    """POST /stock-takes/ — open a new stock take for a location."""

    permission_classes = [IsStorekeeper]
    serializer_class = StockTakeSerializer

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Resolve location, open stock take (freezes system quantities), return serialized."""
        location_id = request.data.get("location")
        if not location_id:
            return Response(
                {"location": "This field is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        location = generics.get_object_or_404(Location, pk=location_id)
        stock_take = open_stock_take(location=location, started_by=request.user)
        st_with_lines = StockTake.objects.prefetch_related("lines").get(pk=stock_take.pk)
        return Response(
            StockTakeSerializer(st_with_lines).data,
            status=status.HTTP_201_CREATED,
        )


class StockTakeDetailView(generics.RetrieveAPIView):
    """GET /stock-takes/{id}/ — fetch a stock take with its count lines."""

    permission_classes = [IsStorekeeper]
    serializer_class = StockTakeSerializer

    def get_queryset(self):
        """Return stock takes with their lines prefetched."""
        return StockTake.objects.prefetch_related("lines")


class StockTakeLinesUpdateView(APIView):
    """PUT /stock-takes/{id}/lines/ — submit counted quantities."""

    permission_classes = [IsStorekeeper]

    def put(self, request: Request, pk: Any, *args: Any, **kwargs: Any) -> Response:
        """Update counted_qty on matching StockTakeLines; return serialized stock take."""
        stock_take = generics.get_object_or_404(StockTake, pk=pk)
        counts_serializer = StockTakeCountsSerializer(data=request.data)
        counts_serializer.is_valid(raise_exception=True)
        counts = counts_serializer.validated_data["counts"]

        lines_map = {
            str(line.product_id): line
            for line in stock_take.lines.all()
        }

        to_update: list[StockTakeLine] = []
        for count in counts:
            product_id = str(count["product"])
            if product_id not in lines_map:
                return Response(
                    {"counts": f"Product {product_id} is not on this stock take."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            line = lines_map[product_id]
            line.counted_qty = count["counted_qty"]
            to_update.append(line)

        StockTakeLine.objects.bulk_update(to_update, ["counted_qty", "updated_at"])
        st_with_lines = StockTake.objects.prefetch_related("lines").get(pk=stock_take.pk)
        return Response(StockTakeSerializer(st_with_lines).data)


class StockTakePostView(APIView):
    """POST /stock-takes/{id}/post/ — compute variances and post adjustments."""

    permission_classes = [IsStorekeeper]

    @idempotent
    def post(self, request: Request, pk: Any, *args: Any, **kwargs: Any) -> Response:
        """Post the stock take identified by pk."""
        stock_take = generics.get_object_or_404(StockTake, pk=pk)
        posted = post_stock_take(stock_take=stock_take, posted_by=request.user)
        st_with_lines = StockTake.objects.prefetch_related("lines").get(pk=posted.pk)
        return Response(StockTakeSerializer(st_with_lines).data)

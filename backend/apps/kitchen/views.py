"""Kitchen display and waiter service endpoints."""

from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import ReasonCode
from apps.kitchen.models import Order, OutOfStockFlag
from apps.kitchen.serializers import (
    ExtraUsageSerializer,
    OrderSerializer,
    OutOfStockSerializer,
    ReturnSerializer,
    ServeSerializer,
)
from apps.kitchen.services import (
    clear_out_of_stock,
    flag_out_of_stock,
    log_extra_usage,
    mark_ready,
    mark_served,
    return_order,
    start_order,
)
from apps.masterdata.models import Product
from apps.menu.models import MenuItem
from apps.users.permissions import IsChef, IsKitchenStaff, IsServiceStaff

_ACTIVE_KITCHEN = [Order.Status.INGESTED, Order.Status.IN_PREPARATION, Order.Status.READY]


class KitchenOrderListView(generics.ListAPIView):
    """GET /api/kitchen/orders/ — active orders for the Chef."""

    serializer_class = OrderSerializer
    permission_classes = [IsKitchenStaff]
    filterset_fields = ["status"]

    def get_queryset(self):
        """Active orders with their lines, oldest first."""
        qs = Order.objects.prefetch_related("items__menu_item").order_by("created_at")
        if "status" in self.request.query_params:
            return qs
        return qs.filter(status__in=_ACTIVE_KITCHEN)


class StartOrderView(APIView):
    """POST /api/kitchen/orders/{id}/start/ — move to In Preparation."""

    permission_classes = [IsChef]

    def post(self, request: Request, pk) -> Response:
        order = get_object_or_404(Order, pk=pk)
        start_order(order=order, user=request.user)
        return Response(OrderSerializer(order).data)


class ReadyOrderView(APIView):
    """POST /api/kitchen/orders/{id}/ready/ — move to Ready."""

    permission_classes = [IsChef]

    def post(self, request: Request, pk) -> Response:
        order = get_object_or_404(Order, pk=pk)
        mark_ready(order=order, user=request.user)
        return Response(OrderSerializer(order).data)


class ExtraUsageView(APIView):
    """POST /api/kitchen/orders/{id}/extra-usage/ — log extra ingredient usage."""

    permission_classes = [IsKitchenStaff]

    def post(self, request: Request, pk) -> Response:
        order = get_object_or_404(Order, pk=pk)
        serializer = ExtraUsageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = get_object_or_404(Product, pk=serializer.validated_data["product"])
        reason = get_object_or_404(ReasonCode, pk=serializer.validated_data["reason_code"])
        entry = log_extra_usage(
            order=order,
            product_id=product.pk,
            qty=serializer.validated_data["qty"],
            reason_code=reason,
            logged_by=request.user,
        )
        return Response({"wastage_entry": str(entry.pk), "status": entry.status})


class WaiterOrderListView(generics.ListAPIView):
    """GET /api/waiter/orders/ — Ready orders, oldest first."""

    serializer_class = OrderSerializer
    permission_classes = [IsServiceStaff]

    def get_queryset(self):
        """Orders awaiting delivery."""
        return (
            Order.objects.filter(status=Order.Status.READY)
            .prefetch_related("items__menu_item")
            .order_by("created_at")
        )


class ServeOrderView(APIView):
    """POST /api/waiter/orders/{id}/served/ — mark delivered."""

    permission_classes = [IsServiceStaff]

    def post(self, request: Request, pk) -> Response:
        order = get_object_or_404(Order, pk=pk)
        serializer = ServeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        mark_served(
            order=order, user=request.user, table_ref=serializer.validated_data["table_ref"]
        )
        return Response(OrderSerializer(order).data)


class ReturnOrderView(APIView):
    """POST /api/waiter/orders/{id}/return/ — flag returned with a reason."""

    permission_classes = [IsServiceStaff]

    def post(self, request: Request, pk) -> Response:
        order = get_object_or_404(Order, pk=pk)
        serializer = ReturnSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = get_object_or_404(ReasonCode, pk=serializer.validated_data["reason_code"])
        return_order(order=order, user=request.user, reason_code=reason)
        return Response(OrderSerializer(order).data)


class OutOfStockListCreateView(generics.ListCreateAPIView):
    """GET/POST /api/kitchen/out-of-stock/ — list or raise OOS flags."""

    serializer_class = OutOfStockSerializer
    permission_classes = [IsChef]

    def get_queryset(self):
        """Uncleared out-of-stock flags."""
        return OutOfStockFlag.objects.filter(cleared_at__isnull=True).order_by("-created_at")

    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        menu_item = get_object_or_404(MenuItem, pk=serializer.validated_data["menu_item_id"])
        flag = flag_out_of_stock(menu_item=menu_item, user=request.user)
        return Response(OutOfStockSerializer(flag).data, status=201)


class OutOfStockClearView(APIView):
    """DELETE /api/kitchen/out-of-stock/{id}/ — clear a flag."""

    permission_classes = [IsChef]

    def delete(self, request: Request, pk) -> Response:
        flag = get_object_or_404(OutOfStockFlag, pk=pk, cleared_at__isnull=True)
        clear_out_of_stock(flag=flag)
        return Response(status=204)

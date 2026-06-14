"""Serializers for kitchen orders and waiter views."""

from rest_framework import serializers

from apps.kitchen.models import Order, OrderItem, OutOfStockFlag


class OrderItemSerializer(serializers.ModelSerializer):
    """Order line with its resolved menu item name."""

    menu_item_name = serializers.CharField(source="menu_item.name", default=None, read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "pos_code", "menu_item_name", "qty", "modifiers", "price"]


class OrderSerializer(serializers.ModelSerializer):
    """Order with its lines and seconds-since-creation for ageing displays."""

    items = OrderItemSerializer(many=True, read_only=True)
    seconds_since_created = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "sale_event",
            "table_ref",
            "status",
            "flagged_insufficient_stock",
            "items",
            "created_at",
            "seconds_since_created",
        ]

    def get_seconds_since_created(self, obj: Order) -> int:
        """Whole seconds since the order was ingested."""
        from django.utils import timezone

        return int((timezone.now() - obj.created_at).total_seconds())


class ExtraUsageSerializer(serializers.Serializer):
    """Payload for logging extra ingredient usage against an order."""

    product = serializers.UUIDField()
    qty = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=0)
    reason_code = serializers.UUIDField()


class ReturnSerializer(serializers.Serializer):
    """Payload for flagging an order returned."""

    reason_code = serializers.UUIDField()


class ServeSerializer(serializers.Serializer):
    """Optional table reference captured at serve time."""

    table_ref = serializers.CharField(required=False, allow_blank=True, default="")


class OutOfStockSerializer(serializers.ModelSerializer):
    """Out-of-stock flag payload."""

    menu_item = serializers.UUIDField(source="menu_item_id")

    class Meta:
        model = OutOfStockFlag
        fields = ["id", "menu_item", "cleared_at", "created_at"]
        read_only_fields = ["id", "cleared_at", "created_at"]

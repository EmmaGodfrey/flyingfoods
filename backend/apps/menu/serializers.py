"""Serializers for menu items and recipe versions."""

from rest_framework import serializers

from apps.menu.models import MenuItem, RecipeLine, RecipeVersion


class MenuItemSerializer(serializers.ModelSerializer):
    """Menu item read/write shape."""

    class Meta:
        model = MenuItem
        fields = ["id", "name", "category", "pos_code", "status", "schedule", "created_at"]
        read_only_fields = ["id", "created_at"]


class RecipeLineSerializer(serializers.ModelSerializer):
    """Recipe ingredient line."""

    product_code = serializers.CharField(source="product.code", read_only=True)

    class Meta:
        model = RecipeLine
        fields = ["id", "product", "product_code", "qty_per_serving"]


class RecipeVersionSerializer(serializers.ModelSerializer):
    """Recipe version with its ingredient lines."""

    lines = RecipeLineSerializer(many=True, read_only=True)

    class Meta:
        model = RecipeVersion
        fields = [
            "id",
            "menu_item",
            "version_no",
            "status",
            "effective_from",
            "effective_to",
            "selling_price_snapshot",
            "lines",
            "created_at",
        ]
        read_only_fields = ["id", "version_no", "status", "created_at"]


class RecipeVersionCreateSerializer(serializers.Serializer):
    """Payload to create the next recipe version."""

    selling_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    lines = serializers.ListField(child=serializers.DictField(), allow_empty=False)


class PublishSerializer(serializers.Serializer):
    """Payload to publish a recipe version."""

    effective_from = serializers.DateField()

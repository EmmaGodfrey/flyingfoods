"""Serializers for masterdata resources."""

from rest_framework import serializers

from apps.masterdata.models import Category, Location, Product, Supplier


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for Category — used internally by ProductSerializer."""

    class Meta:
        model = Category
        fields = ["id", "name", "is_active"]


class LocationSerializer(serializers.ModelSerializer):
    """Serializer for Location list endpoint."""

    class Meta:
        model = Location
        fields = ["id", "name", "kind"]


class ProductSerializer(serializers.ModelSerializer):
    """Full product serializer: creation and detail views."""

    class Meta:
        model = Product
        fields = [
            "id",
            "code",
            "name",
            "category",
            "stock_uom",
            "purchase_uom",
            "recipe_uom",
            "purchase_to_stock_factor",
            "recipe_to_stock_factor",
            "reorder_level",
            "pastel_code",
            "is_active",
            "created_at",
            "updated_at",
        ]


class ProductListSerializer(serializers.ModelSerializer):
    """Compact product representation for list views."""

    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "code",
            "name",
            "category",
            "category_name",
            "stock_uom",
            "reorder_level",
            "is_active",
        ]


class SupplierSerializer(serializers.ModelSerializer):
    """Full supplier serializer for create and detail views."""

    class Meta:
        model = Supplier
        fields = [
            "id",
            "name",
            "contact_name",
            "email",
            "phone",
            "approval_status",
            "payment_terms",
            "is_active",
            "created_at",
            "updated_at",
        ]

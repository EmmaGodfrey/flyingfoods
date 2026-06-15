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
    """Full product serializer: creation and detail views.

    ``category`` is read and written as a plain name; the matching Category is
    created on demand so the admin form's free-text category just works.
    """

    category = serializers.CharField()

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

    def _resolve_category(self, validated_data: dict) -> None:
        """Replace the category name with its Category instance, creating it if new."""
        name = validated_data.get("category")
        if isinstance(name, str):
            validated_data["category"] = Category.objects.get_or_create(name=name)[0]

    def create(self, validated_data: dict) -> Product:
        """Create a product, resolving the category name to an instance."""
        self._resolve_category(validated_data)
        return super().create(validated_data)

    def update(self, instance: Product, validated_data: dict) -> Product:
        """Update a product, resolving the category name to an instance."""
        self._resolve_category(validated_data)
        return super().update(instance, validated_data)

    def to_representation(self, instance: Product) -> dict:
        """Render category as its name, not the raw foreign key."""
        rep = super().to_representation(instance)
        rep["category"] = instance.category.name if instance.category_id else None
        return rep


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

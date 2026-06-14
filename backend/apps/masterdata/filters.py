"""Django-filter FilterSets for masterdata resources."""

import django_filters

from apps.masterdata.models import Product, Supplier


class ProductFilter(django_filters.FilterSet):
    """Filterset for the product list endpoint.

    Supported query params: category (FK id), is_active (bool).
    below_reorder filter added with inventory app.
    """

    category = django_filters.UUIDFilter(field_name="category__id")
    is_active = django_filters.BooleanFilter(field_name="is_active")

    class Meta:
        model = Product
        fields = ["category", "is_active"]


class SupplierFilter(django_filters.FilterSet):
    """Filterset for the supplier list endpoint."""

    is_active = django_filters.BooleanFilter(field_name="is_active")
    approval_status = django_filters.CharFilter(field_name="approval_status")

    class Meta:
        model = Supplier
        fields = ["is_active", "approval_status"]

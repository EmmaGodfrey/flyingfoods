"""Django-filter filtersets for inventory list endpoints."""

import django_filters
from django.db.models import F, QuerySet

from apps.inventory.models import StockBalance, StockMovement


class StockBalanceFilter(django_filters.FilterSet):
    """Filters for GET /stock/balances/."""

    location = django_filters.UUIDFilter(field_name="location__id")
    product = django_filters.UUIDFilter(field_name="product__id")
    below_reorder = django_filters.BooleanFilter(method="filter_below_reorder")

    class Meta:
        model = StockBalance
        fields = ["location", "product", "below_reorder"]

    def filter_below_reorder(self, queryset: QuerySet, name: str, value: bool) -> QuerySet:
        """Filter balances where qty_on_hand <= product.reorder_level using F()."""
        if value is True:
            return queryset.filter(qty_on_hand__lte=F("product__reorder_level"))
        if value is False:
            return queryset.filter(qty_on_hand__gt=F("product__reorder_level"))
        return queryset


class StockMovementFilter(django_filters.FilterSet):
    """Filters for GET /stock/movements/."""

    product = django_filters.UUIDFilter(field_name="product__id")
    location = django_filters.UUIDFilter(field_name="location__id")
    movement_type = django_filters.ChoiceFilter(
        field_name="movement_type",
        choices=StockMovement.MovementType.choices,
    )
    document_type = django_filters.CharFilter(field_name="document_type")
    posted_after = django_filters.DateTimeFilter(
        field_name="posted_at", lookup_expr="gte"
    )
    posted_before = django_filters.DateTimeFilter(
        field_name="posted_at", lookup_expr="lte"
    )

    class Meta:
        model = StockMovement
        fields = [
            "product",
            "location",
            "movement_type",
            "document_type",
            "posted_after",
            "posted_before",
        ]

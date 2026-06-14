"""Django-filter FilterSets for core models."""

import django_filters

from apps.core.models import Approval, ReasonCode, ThresholdConfig


class ReasonCodeFilter(django_filters.FilterSet):
    """Filterset for reason code list endpoint."""

    category = django_filters.CharFilter(field_name="category")
    is_active = django_filters.BooleanFilter(field_name="is_active")

    class Meta:
        model = ReasonCode
        fields = ["category", "is_active"]


class ThresholdConfigFilter(django_filters.FilterSet):
    """Filterset for threshold config list endpoint."""

    scope = django_filters.CharFilter(field_name="scope")
    is_active = django_filters.BooleanFilter(field_name="is_active")

    class Meta:
        model = ThresholdConfig
        fields = ["scope", "is_active"]


class ApprovalFilter(django_filters.FilterSet):
    """Filterset for approval queue endpoint."""

    status = django_filters.CharFilter(field_name="status")
    scope = django_filters.CharFilter(field_name="scope")

    class Meta:
        model = Approval
        fields = ["status", "scope"]

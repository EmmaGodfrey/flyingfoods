"""Report serializers.

Reports are read-only aggregations returned as plain dicts from selectors.
This module provides DRF serializers for validating query parameters where
the logic is complex enough to warrant it. Simple param parsing lives in
the views themselves.
"""

import datetime

from rest_framework import serializers


class DateRangeParamsSerializer(serializers.Serializer):
    """Validate optional ``date_from`` / ``date_to`` query parameters."""

    date_from = serializers.DateField(required=False, allow_null=True)
    date_to = serializers.DateField(required=False, allow_null=True)

    def validate(self, attrs: dict) -> dict:
        """Ensure date_from is not after date_to when both are provided."""
        d_from = attrs.get("date_from")
        d_to = attrs.get("date_to")
        if d_from and d_to and d_from > d_to:
            raise serializers.ValidationError(
                "date_from must not be later than date_to."
            )
        return attrs

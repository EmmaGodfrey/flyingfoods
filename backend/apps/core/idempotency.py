"""Idempotency guard for stock-posting endpoints.

Clients send an `Idempotency-Key` header on POSTs that move stock. A retry
with the same key returns the stored response instead of double-posting.
"""

import functools
from typing import Any, Callable

from django.db import IntegrityError
from rest_framework.response import Response

from apps.core.models import IdempotencyKey


def idempotent(view_method: Callable[..., Response]) -> Callable[..., Response]:
    """Decorator for DRF view methods honoring the Idempotency-Key header."""

    @functools.wraps(view_method)
    def wrapper(self: Any, request: Any, *args: Any, **kwargs: Any) -> Response:
        key = request.headers.get("Idempotency-Key")
        if not key:
            return view_method(self, request, *args, **kwargs)

        existing = IdempotencyKey.objects.filter(key=key).first()
        if existing is not None:
            return Response(existing.response_snapshot, status=existing.status_code)

        response = view_method(self, request, *args, **kwargs)
        if 200 <= response.status_code < 300:
            try:
                IdempotencyKey.objects.create(
                    key=key,
                    endpoint=request.path,
                    response_snapshot=response.data,
                    status_code=response.status_code,
                )
            except IntegrityError:
                # Concurrent retry won the race; its stored response is identical.
                pass
        return response

    return wrapper

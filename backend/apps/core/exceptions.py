"""Project exception types and the global handler producing the error envelope."""

import logging
from typing import Any, Mapping, Optional

from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


class DomainError(APIException):
    """Base class for business-rule violations carrying a stable error code."""

    status_code = status.HTTP_409_CONFLICT
    default_code = "DOMAIN_ERROR"
    default_detail = "Business rule violated."


class InsufficientStockError(DomainError):
    default_code = "INSUFFICIENT_STOCK"
    default_detail = "Posting would drive stock on hand below zero."


class ApprovalPendingError(DomainError):
    default_code = "APPROVAL_PENDING"
    default_detail = "A required approval has not been resolved."


class AlreadyServedError(DomainError):
    default_code = "ALREADY_SERVED"
    default_detail = "Order has already been marked served."


class HasHistoryError(DomainError):
    default_code = "MENU_ITEM_HAS_HISTORY"
    default_detail = "Record has historical transactions; deactivate it instead."


class ImmutableVersionError(DomainError):
    default_code = "RECIPE_VERSION_IMMUTABLE"
    default_detail = "Published recipe versions cannot be edited."


class OffScheduleReasonRequired(ValidationError):
    default_code = "OFF_SCHEDULE_REASON_REQUIRED"
    default_detail = "Issues to the Unit outside Tue/Thu require a reason."


def _error_code(exc: Exception, response: Response) -> str:
    """Map an exception to its stable machine-readable code."""
    if isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
        return "AUTH_REQUIRED"
    if isinstance(exc, PermissionDenied):
        return "FORBIDDEN_ROLE"
    if isinstance(exc, Http404):
        return "NOT_FOUND"
    if isinstance(exc, DomainError):
        return str(exc.get_codes())
    if isinstance(exc, ValidationError):
        codes = exc.get_codes()
        if isinstance(codes, list) and codes and isinstance(codes[0], str) and codes[0].isupper():
            return codes[0]
        return "VALIDATION_ERROR"
    if response.status_code >= 500:
        return "INTERNAL_ERROR"
    return "ERROR"


def _error_message(exc: Exception) -> str:
    """Human-readable message; never leaks internals for server errors."""
    if isinstance(exc, ValidationError):
        detail = exc.detail
        if isinstance(detail, dict):
            first_key = next(iter(detail))
            first = detail[first_key]
            text = first[0] if isinstance(first, list) else first
            return f"{first_key}: {text}"
        if isinstance(detail, list) and detail:
            return str(detail[0])
    return str(getattr(exc, "detail", exc))


def envelope_exception_handler(
    exc: Exception, context: Mapping[str, Any]
) -> Optional[Response]:
    """Convert every API error into {"success": false, "error": {code, message}}."""
    response = drf_exception_handler(exc, context)
    if response is None:
        logger.exception("Unhandled API error", exc_info=exc)
        response = Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        response.data = {}
        code, message = "INTERNAL_ERROR", "An internal error occurred."
    else:
        code = _error_code(exc, response)
        message = (
            "An internal error occurred."
            if response.status_code >= 500
            else _error_message(exc)
        )
    details = response.data if isinstance(response.data, (dict, list)) else None
    response.data = {
        "_enveloped": True,
        "success": False,
        "error": {"code": code, "message": message, "details": details},
    }
    return response

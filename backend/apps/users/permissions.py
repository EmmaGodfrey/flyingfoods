"""Role-based DRF permission classes. ADMIN passes every check."""

from typing import Iterable

from rest_framework.permissions import BasePermission

from apps.users.models import User


def _has_role(request, roles: Iterable[str]) -> bool:
    """True when the requester is authenticated and holds one of the roles."""
    return bool(
        request.user
        and request.user.is_authenticated
        and (request.user.role in roles or request.user.role == User.Role.ADMIN)
    )


class IsAdmin(BasePermission):
    """System Administrators only."""

    def has_permission(self, request, view) -> bool:
        return _has_role(request, (User.Role.ADMIN,))


class IsManager(BasePermission):
    """Managers (and Admins)."""

    def has_permission(self, request, view) -> bool:
        return _has_role(request, (User.Role.MANAGER,))


class IsChef(BasePermission):
    """Chefs (and Admins)."""

    def has_permission(self, request, view) -> bool:
        return _has_role(request, (User.Role.CHEF,))


class IsWaiter(BasePermission):
    """Waiters (and Admins)."""

    def has_permission(self, request, view) -> bool:
        return _has_role(request, (User.Role.WAITER,))


class IsStorekeeper(BasePermission):
    """Storekeepers (and Admins)."""

    def has_permission(self, request, view) -> bool:
        return _has_role(request, (User.Role.STOREKEEPER,))


class IsReceivingOfficer(BasePermission):
    """Receiving Officers (and Admins)."""

    def has_permission(self, request, view) -> bool:
        return _has_role(request, (User.Role.RECEIVING_OFFICER,))


class IsIssuer(BasePermission):
    """Storekeeper, Restaurant and Unit Issuers (and Admins) — may issue stock."""

    def has_permission(self, request, view) -> bool:
        return _has_role(
            request,
            (
                User.Role.STOREKEEPER,
                User.Role.RESTAURANT_ISSUER,
                User.Role.UNIT_ISSUER,
            ),
        )


class IsKitchenStaff(BasePermission):
    """Chef, Storekeeper, or Manager — kitchen-adjacent read/write."""

    def has_permission(self, request, view) -> bool:
        return _has_role(
            request, (User.Role.CHEF, User.Role.STOREKEEPER, User.Role.MANAGER)
        )


class IsServiceStaff(BasePermission):
    """Waiter or Manager — service views."""

    def has_permission(self, request, view) -> bool:
        return _has_role(request, (User.Role.WAITER, User.Role.MANAGER))


class IsStockViewer(BasePermission):
    """Roles allowed to read stock: storekeeper, issuers, manager."""

    def has_permission(self, request, view) -> bool:
        return _has_role(
            request,
            (
                User.Role.STOREKEEPER,
                User.Role.MANAGER,
                User.Role.RESTAURANT_ISSUER,
                User.Role.UNIT_ISSUER,
                User.Role.RECEIVING_OFFICER,
            ),
        )


class IsProcurementStaff(BasePermission):
    """Receiving Officer or Manager."""

    def has_permission(self, request, view) -> bool:
        return _has_role(
            request, (User.Role.RECEIVING_OFFICER, User.Role.MANAGER)
        )

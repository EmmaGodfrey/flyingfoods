"""Kitchen and waiter write services: status lifecycle, extra usage, returns."""

from decimal import Decimal
from typing import Any, Optional

from django.db import transaction
from django.utils import timezone

from apps.core.exceptions import AlreadyServedError, ApprovalPendingError
from apps.core.models import Approval
from apps.core.services import log_audit
from apps.kitchen.models import Order, OrderStatusEvent, OutOfStockFlag
from apps.kitchen.realtime import broadcast_order_event
from apps.menu.models import MenuItem
from apps.notifications.services import notify_role
from apps.users.models import User


def _record_status(order: Order, status: str, user: Optional[Any], reason_code=None) -> None:
    """Persist a status transition and broadcast it."""
    order.status = status
    order.save(update_fields=["status", "updated_at"])
    OrderStatusEvent.objects.create(order=order, status=status, user=user, reason_code=reason_code)
    log_audit(entity="Order", entity_id=order.pk, action=status, user=user)
    transaction.on_commit(lambda: broadcast_order_event("order.status", order.pk))


@transaction.atomic
def start_order(*, order: Order, user: Any) -> Order:
    """Move an order to In Preparation."""
    _record_status(order, Order.Status.IN_PREPARATION, user)
    return order


@transaction.atomic
def mark_ready(*, order: Order, user: Any) -> Order:
    """Move an order to Ready, blocked while extra-usage approval is pending."""
    pending = Approval.objects.filter(
        scope="EXTRA_USAGE", status=Approval.Status.PENDING, subject_id=order.pk
    ).exists()
    if pending:
        raise ApprovalPendingError("Resolve the extra-usage approval before marking ready.")
    _record_status(order, Order.Status.READY, user)
    return order


@transaction.atomic
def mark_served(*, order: Order, user: Any, table_ref: str = "") -> Order:
    """Mark a Ready order Served. Re-serving is a conflict, not a silent no-op."""
    if order.status == Order.Status.SERVED:
        raise AlreadyServedError()
    if table_ref:
        order.table_ref = table_ref
        order.save(update_fields=["table_ref", "updated_at"])
    _record_status(order, Order.Status.SERVED, user)
    return order


@transaction.atomic
def return_order(*, order: Order, user: Any, reason_code) -> Order:
    """Flag an order Returned and send it back to In Preparation, alerting the Chef."""
    OrderStatusEvent.objects.create(
        order=order, status=Order.Status.RETURNED, user=user, reason_code=reason_code
    )
    log_audit(entity="Order", entity_id=order.pk, action="RETURNED", user=user)
    _record_status(order, Order.Status.IN_PREPARATION, user, reason_code=reason_code)
    notify_role(
        User.Role.CHEF,
        kind="ORDER_RETURNED",
        body=f"Order {order.sale_event_id} returned: {reason_code.label if reason_code else 'no reason'}.",
        subject=order,
    )
    return order


@transaction.atomic
def log_extra_usage(*, order: Order, product_id: Any, qty: Decimal, reason_code, logged_by: Any):
    """Record extra ingredient usage against an active order.

    Delegates to the wastage service so the entry lands in the wastage
    ledger, gets threshold-routed, and posts a stock deduction.
    """
    from apps.wastage.services import create_extra_usage

    return create_extra_usage(
        order=order,
        product_id=product_id,
        qty=qty,
        reason_code=reason_code,
        logged_by=logged_by,
    )


@transaction.atomic
def flag_out_of_stock(*, menu_item: MenuItem, user: Any) -> OutOfStockFlag:
    """Raise an out-of-stock flag for a menu item."""
    return OutOfStockFlag.objects.create(menu_item=menu_item, flagged_by=user)


@transaction.atomic
def clear_out_of_stock(*, flag: OutOfStockFlag) -> OutOfStockFlag:
    """Clear an out-of-stock flag."""
    flag.cleared_at = timezone.now()
    flag.save(update_fields=["cleared_at", "updated_at"])
    return flag

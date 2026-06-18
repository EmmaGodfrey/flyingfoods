"""POS sale-event ingestion: dedupe, order creation, recipe deduction."""

from decimal import Decimal
from typing import Any, Optional

from django.db import IntegrityError, transaction
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import ValidationError

from apps.core.exceptions import InsufficientStockError
from apps.core.services import log_audit
from apps.inventory.models import StockMovement
from apps.inventory.services import MovementLine, post_movements
from apps.kitchen.models import Order, OrderItem, OrderStatusEvent
from apps.kitchen.realtime import broadcast_order_event
from apps.masterdata.models import Location
from apps.menu.models import MenuItem, RecipeVersion
from apps.notifications.services import notify_role
from apps.notifications.models import Notification
from apps.pos_ingest.models import ReplayLog, SaleEvent
from apps.users.models import User


def _stores_location() -> Location:
    """The central Restaurant Stores location deductions draw from."""
    stores = Location.objects.filter(kind=Location.Kind.STORES).first()
    if stores is None:
        raise ValidationError({"detail": "Restaurant Stores location is not configured."})
    return stores


def _deduction_lines(order: Order, stores: Location) -> Optional[list[MovementLine]]:
    """Build recipe-driven deduction lines; None when any item lacks a recipe."""
    lines: dict[Any, Decimal] = {}
    for item in order.items.select_related("recipe_version"):
        if item.recipe_version is None:
            return None
        for recipe_line in item.recipe_version.lines.select_related("product"):
            stock_qty = (
                recipe_line.qty_per_serving
                * recipe_line.product.recipe_to_stock_factor
                * item.qty
            )
            lines[recipe_line.product_id] = lines.get(recipe_line.product_id, Decimal("0")) + stock_qty
    return [
        MovementLine(
            product_id=product_id,
            location_id=stores.pk,
            qty_delta=-qty,
            movement_type=StockMovement.MovementType.SALE_DEDUCTION,
        )
        for product_id, qty in lines.items()
    ]


@transaction.atomic
def ingest_sale_event(payload: dict) -> SaleEvent:
    """Ingest one POS sale exactly once, keyed on the POS sale ID.

    Duplicate sale IDs return the existing event unchanged. Unknown menu
    items flag the event and skip deduction (FR-PI-05). Insufficient stock
    flags the order and alerts the Storekeeper but does not block the
    kitchen ticket (FR-KD-05).
    """
    pos_sale_id = payload.get("pos_sale_id")
    if not pos_sale_id:
        raise ValidationError({"pos_sale_id": "Required."})
    sold_at = parse_datetime(str(payload.get("sold_at", ""))) if payload.get("sold_at") else None
    if sold_at is None:
        raise ValidationError({"sold_at": "Valid ISO datetime required."})
    raw_lines = payload.get("lines") or []
    if not raw_lines:
        raise ValidationError({"lines": "At least one sale line is required."})

    existing = SaleEvent.objects.filter(pos_sale_id=pos_sale_id).first()
    if existing is not None:
        return existing
    try:
        # Savepoint so a racing duplicate's IntegrityError does not poison
        # the surrounding transaction.
        with transaction.atomic():
            event = SaleEvent.objects.create(
                pos_sale_id=pos_sale_id,
                payload=payload,
                cashier=str(payload.get("cashier", "")),
                sold_at=sold_at,
                totals=payload.get("totals") or {},
            )
    except IntegrityError:
        return SaleEvent.objects.get(pos_sale_id=pos_sale_id)

    order = Order.objects.create(
        sale_event=event, table_ref=str(payload.get("table_ref", ""))
    )
    unknown_item = False
    for raw in raw_lines:
        pos_code = str(raw.get("pos_code", ""))
        menu_item = MenuItem.objects.filter(pos_code=pos_code).first()
        recipe_version = (
            RecipeVersion.active_for(menu_item.pk, sold_at.date()) if menu_item else None
        )
        if menu_item is None or recipe_version is None:
            unknown_item = True
        OrderItem.objects.create(
            order=order,
            menu_item=menu_item,
            recipe_version=recipe_version,
            pos_code=pos_code,
            qty=Decimal(str(raw.get("qty", 1))),
            modifiers=raw.get("modifiers") or [],
            price=raw.get("price"),
        )
    OrderStatusEvent.objects.create(order=order, status=Order.Status.INGESTED)

    if unknown_item:
        event.status = SaleEvent.Status.FLAGGED_UNKNOWN_ITEM
        event.save(update_fields=["status", "updated_at"])
        notify_role(
            User.Role.ADMIN,
            kind=Notification.Kind.UNKNOWN_MENU_ITEM,
            body=f"Sale {pos_sale_id} references an unknown menu item or unpublished recipe.",
            subject=event,
        )
    else:
        stores = _stores_location()
        deductions = _deduction_lines(order, stores)
        try:
            post_movements(
                document_type="Order",
                document_id=order.pk,
                lines=deductions,
                posted_by=None,
            )
        except InsufficientStockError:
            # Kitchen still gets the ticket; stock goes negative-aware path:
            # flag the order and alert the Storekeeper (FR-KD-05).
            order.flagged_insufficient_stock = True
            order.save(update_fields=["flagged_insufficient_stock", "updated_at"])
            notify_role(
                User.Role.STOREKEEPER,
                kind="INSUFFICIENT_STOCK",
                body=f"Order {pos_sale_id}: recipe ingredients insufficient in stock.",
                subject=order,
            )
            post_movements(
                document_type="Order",
                document_id=order.pk,
                lines=deductions,
                posted_by=None,
                allow_negative=True,
            )

    log_audit(entity="SaleEvent", entity_id=event.pk, action="INGEST", after={"pos_sale_id": pos_sale_id})
    transaction.on_commit(lambda: broadcast_order_event("order.created", order.pk))
    return event


@transaction.atomic
def replay_sale_event(*, event: SaleEvent, replayed_by: Any) -> SaleEvent:
    """Re-run ingestion side effects for a flagged/failed event (FR-PI-06).

    Replay re-resolves menu items (e.g. after the Administrator published
    the missing recipe) and posts the deduction if it never happened.
    """
    ReplayLog.objects.create(sale_event=event, replayed_by=replayed_by)
    order = getattr(event, "order", None)
    if order is None:
        raise ValidationError({"detail": "Event has no order; cannot replay."})

    resolved_all = True
    for item in order.items.all():
        if item.recipe_version is None:
            menu_item = MenuItem.objects.filter(pos_code=item.pos_code).first()
            recipe_version = (
                RecipeVersion.active_for(menu_item.pk, event.sold_at.date())
                if menu_item
                else None
            )
            if menu_item and recipe_version:
                item.menu_item = menu_item
                item.recipe_version = recipe_version
                item.save(update_fields=["menu_item", "recipe_version", "updated_at"])
            else:
                resolved_all = False

    if resolved_all:
        stores = _stores_location()
        deductions = _deduction_lines(order, stores)
        if deductions:
            post_movements(
                document_type="Order",
                document_id=order.pk,
                lines=deductions,
                posted_by=replayed_by,
                allow_negative=True,
            )
        event.status = SaleEvent.Status.REPLAYED
    else:
        event.status = SaleEvent.Status.FLAGGED_UNKNOWN_ITEM
    event.save(update_fields=["status", "updated_at"])
    log_audit(
        entity="SaleEvent",
        entity_id=event.pk,
        action="REPLAY",
        user=replayed_by,
        after={"resolved": resolved_all},
    )
    return event

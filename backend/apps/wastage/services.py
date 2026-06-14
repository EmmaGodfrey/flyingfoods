"""Wastage write services: logging, threshold routing, and stock posting."""

from decimal import Decimal
from typing import Any, Optional

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.core.models import ThresholdConfig
from apps.core.services import log_audit, requires_approval, submit_for_approval
from apps.inventory.models import StockMovement
from apps.inventory.services import MovementLine, _latest_unit_cost, post_movements
from apps.masterdata.models import Location
from apps.wastage.models import WastageEntry


def _resolve_location(order, explicit_location_id: Optional[Any]) -> Any:
    """Pick the location for a wastage entry: explicit, else Restaurant Stores."""
    if explicit_location_id is not None:
        return explicit_location_id
    stores = Location.objects.filter(kind=Location.Kind.STORES).values_list("pk", flat=True).first()
    if stores is None:
        raise ValidationError({"location": "No location given and Stores is not configured."})
    return stores


@transaction.atomic
def _route_and_post(*, entry: WastageEntry, scope: str, posted_by: Any) -> WastageEntry:
    """Either post immediately or open a Manager approval, by threshold."""
    if requires_approval(scope, entry.value):
        entry.status = WastageEntry.Status.PENDING_APPROVAL
        entry.save(update_fields=["status", "updated_at"])
        submit_for_approval(
            subject=entry, scope=scope, requested_by=posted_by, value=entry.value
        )
        return entry
    return post_wastage_entry(entry=entry, posted_by=posted_by, skip_approval=True)


@transaction.atomic
def create_extra_usage(*, order, product_id: Any, qty: Decimal, reason_code, logged_by: Any) -> WastageEntry:
    """Log extra ingredient usage against an active order (FR-KD-07/FR-WA-01)."""
    if qty <= 0:
        raise ValidationError({"qty": "Quantity must be positive."})
    location_id = _resolve_location(order, None)
    value = _latest_unit_cost(product_id) * qty
    entry = WastageEntry.objects.create(
        entry_type=WastageEntry.EntryType.EXTRA_USAGE,
        order=order,
        product_id=product_id,
        location_id=location_id,
        qty=qty,
        reason_code=reason_code,
        value=value,
        logged_by=logged_by,
    )
    return _route_and_post(entry=entry, scope=ThresholdConfig.Scope.EXTRA_USAGE, posted_by=logged_by)


@transaction.atomic
def create_wastage(
    *,
    entry_type: str,
    product_id: Any,
    location_id: Any,
    qty: Decimal,
    reason_code,
    logged_by: Any,
    note: str = "",
) -> WastageEntry:
    """Log a breakage or spoilage event (FR-WA-02)."""
    if qty <= 0:
        raise ValidationError({"qty": "Quantity must be positive."})
    value = _latest_unit_cost(product_id) * qty
    entry = WastageEntry.objects.create(
        entry_type=entry_type,
        product_id=product_id,
        location_id=location_id,
        qty=qty,
        reason_code=reason_code,
        note=note,
        value=value,
        logged_by=logged_by,
    )
    return _route_and_post(entry=entry, scope=ThresholdConfig.Scope.WASTAGE, posted_by=logged_by)


@transaction.atomic
def post_wastage_entry(*, entry: WastageEntry, posted_by: Any, skip_approval: bool = False) -> WastageEntry:
    """Deduct the wasted quantity from stock and mark the entry posted."""
    if entry.status == WastageEntry.Status.POSTED:
        return entry
    post_movements(
        document_type="WastageEntry",
        document_id=entry.pk,
        lines=[
            MovementLine(
                product_id=entry.product_id,
                location_id=entry.location_id,
                qty_delta=-entry.qty,
                movement_type=StockMovement.MovementType.WASTAGE,
            )
        ],
        posted_by=posted_by,
        allow_negative=True,
    )
    entry.status = WastageEntry.Status.POSTED
    entry.save(update_fields=["status", "updated_at"])
    log_audit(entity="WastageEntry", entity_id=entry.pk, action="POST", user=posted_by)
    return entry

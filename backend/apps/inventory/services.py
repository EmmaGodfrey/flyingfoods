"""Inventory write services. `post_movements` is the ONLY ledger writer.

Every stock change in the system funnels through `post_movements`, which
enforces the parent-document requirement, the negative-stock guard, audit
logging, and atomic outbox creation for Pastel sync.
"""

import datetime
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Optional, Sequence

from django.db import models, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.exceptions import InsufficientStockError
from apps.core.models import OutboxRecord, ThresholdConfig
from apps.core.services import log_audit, requires_approval, submit_for_approval
from apps.inventory.models import (
    IssueNote,
    StockBalance,
    StockMovement,
    StockTake,
    StockTakeLine,
    Transfer,
)
from apps.masterdata.models import Location, Product


@dataclass(frozen=True)
class MovementLine:
    """One requested ledger entry."""

    product_id: Any
    location_id: Any
    qty_delta: Decimal
    movement_type: str
    unit_cost: Optional[Decimal] = None


UNIT_ISSUE_DAYS = (1, 3)  # Tuesday, Thursday (date.weekday(): Mon=0)


def _latest_unit_cost(product_id: Any) -> Decimal:
    """Most recent GRN unit cost for a product, falling back to zero."""
    row = (
        StockMovement.objects.filter(
            product_id=product_id,
            movement_type=StockMovement.MovementType.GRN_RECEIPT,
            unit_cost__isnull=False,
        )
        .order_by("-posted_at")
        .values("unit_cost")
        .first()
    )
    return row["unit_cost"] if row else Decimal("0")


def lines_value(lines: Sequence[tuple[Any, Decimal]]) -> Decimal:
    """Monetary value of (product_id, qty) pairs at latest GRN cost."""
    return sum(
        (_latest_unit_cost(product_id) * qty for product_id, qty in lines),
        Decimal("0"),
    )


@transaction.atomic
def post_movements(
    *,
    document_type: str,
    document_id: Any,
    lines: Sequence[MovementLine],
    posted_by: Optional[Any] = None,
    allow_negative: bool = False,
) -> list[StockMovement]:
    """Append ledger rows for one document, atomically with balances and outbox.

    Raises InsufficientStockError when any line would drive on-hand below
    zero and `allow_negative` is False. Idempotent per document: posting the
    same document twice is a no-op returning the existing rows.
    """
    if not lines:
        raise ValidationError({"lines": "At least one movement line is required."})

    existing = list(
        StockMovement.objects.filter(
            document_type=document_type, document_id=document_id
        )
    )
    if existing:
        return existing

    movements: list[StockMovement] = []
    outbox_lines: list[dict] = []

    for line in lines:
        if line.qty_delta == 0:
            raise ValidationError({"lines": "Zero-quantity movement is meaningless."})
        balance, _ = (
            StockBalance.objects.select_for_update()
            .get_or_create(product_id=line.product_id, location_id=line.location_id)
        )
        new_qty = balance.qty_on_hand + line.qty_delta
        if new_qty < 0 and not allow_negative:
            raise InsufficientStockError(
                f"Product {line.product_id} at location {line.location_id}: "
                f"on hand {balance.qty_on_hand}, requested {line.qty_delta}."
            )
        movement = StockMovement.objects.create(
            product_id=line.product_id,
            location_id=line.location_id,
            qty_delta=line.qty_delta,
            movement_type=line.movement_type,
            document_type=document_type,
            document_id=document_id,
            unit_cost=line.unit_cost,
            posted_by=posted_by,
        )
        balance.qty_on_hand = new_qty
        balance.last_movement_at = movement.posted_at
        balance.save(update_fields=["qty_on_hand", "last_movement_at", "updated_at"])
        movements.append(movement)
        outbox_lines.append(
            {
                "movement_id": str(movement.pk),
                "product_id": str(line.product_id),
                "location_id": str(line.location_id),
                "qty_delta": str(line.qty_delta),
                "movement_type": line.movement_type,
                "unit_cost": str(line.unit_cost) if line.unit_cost is not None else None,
            }
        )

    OutboxRecord.objects.create(
        entity_type=document_type,
        entity_id=document_id,
        payload={
            "document_type": document_type,
            "document_id": str(document_id),
            "posted_at": timezone.now().isoformat(),
            "lines": outbox_lines,
        },
    )
    log_audit(
        entity=document_type,
        entity_id=document_id,
        action="POST_MOVEMENTS",
        user=posted_by,
        after={"lines": outbox_lines},
    )
    return movements


def on_hand(product_id: Any, location_id: Any) -> Decimal:
    """Current cached on-hand for a product at a location."""
    row = (
        StockBalance.objects.filter(product_id=product_id, location_id=location_id)
        .values("qty_on_hand")
        .first()
    )
    return row["qty_on_hand"] if row else Decimal("0")


def create_issue_note(
    *,
    source: Location,
    destination: Location,
    requested_by: Any,
    lines: Sequence[tuple[Any, Decimal]],
    off_schedule_reason_id: Optional[Any] = None,
) -> IssueNote:
    """Create a draft issue note, enforcing the Unit Tue/Thu schedule warning."""
    if not lines:
        raise ValidationError({"lines": "At least one line is required."})
    if destination.kind == Location.Kind.UNIT:
        today = datetime.date.today()
        if today.weekday() not in UNIT_ISSUE_DAYS and off_schedule_reason_id is None:
            raise ValidationError(
                {"off_schedule_reason": "Issues to the Unit outside Tue/Thu require a reason."},
                code="OFF_SCHEDULE_REASON_REQUIRED",
            )
    note = IssueNote.objects.create(
        source=source,
        destination=destination,
        requested_by=requested_by,
        off_schedule_reason_id=off_schedule_reason_id,
    )
    note.lines.bulk_create(
        [
            note.lines.model(issue_note=note, product_id=product_id, qty=qty)
            for product_id, qty in lines
        ]
    )
    return note


@transaction.atomic
def post_issue_note(
    *, issue_note: IssueNote, posted_by: Any, allow_negative: bool = False
) -> IssueNote:
    """Post a draft issue: deduct source, add destination, mirror to Pastel."""
    if issue_note.status == IssueNote.Status.POSTED:
        return issue_note
    lines = list(issue_note.lines.all())
    movement_lines: list[MovementLine] = []
    for line in lines:
        movement_lines.append(
            MovementLine(
                product_id=line.product_id,
                location_id=issue_note.source_id,
                qty_delta=-line.qty,
                movement_type=StockMovement.MovementType.ISSUE_OUT,
            )
        )
        movement_lines.append(
            MovementLine(
                product_id=line.product_id,
                location_id=issue_note.destination_id,
                qty_delta=line.qty,
                movement_type=StockMovement.MovementType.ISSUE_IN,
            )
        )
    post_movements(
        document_type="IssueNote",
        document_id=issue_note.pk,
        lines=movement_lines,
        posted_by=posted_by,
        allow_negative=allow_negative,
    )
    issue_note.status = IssueNote.Status.POSTED
    issue_note.save(update_fields=["status", "updated_at"])
    return issue_note


@transaction.atomic
def post_transfer(
    *, transfer: Transfer, posted_by: Any, skip_approval: bool = False
) -> Transfer:
    """Post a transfer, routing above-threshold values to Manager approval."""
    if transfer.status == Transfer.Status.POSTED:
        return transfer
    lines = list(transfer.lines.all())
    if not lines:
        raise ValidationError({"lines": "Transfer has no lines."})

    value = lines_value([(line.product_id, line.qty) for line in lines])
    transfer.total_value = value

    if not skip_approval and requires_approval(ThresholdConfig.Scope.TRANSFER, value):
        transfer.status = Transfer.Status.PENDING_APPROVAL
        transfer.save(update_fields=["status", "total_value", "updated_at"])
        submit_for_approval(
            subject=transfer,
            scope=ThresholdConfig.Scope.TRANSFER,
            requested_by=posted_by,
            value=value,
        )
        return transfer

    movement_lines: list[MovementLine] = []
    for line in lines:
        movement_lines.append(
            MovementLine(
                product_id=line.product_id,
                location_id=transfer.source_id,
                qty_delta=-line.qty,
                movement_type=StockMovement.MovementType.TRANSFER_OUT,
            )
        )
        movement_lines.append(
            MovementLine(
                product_id=line.product_id,
                location_id=transfer.destination_id,
                qty_delta=line.qty,
                movement_type=StockMovement.MovementType.TRANSFER_IN,
            )
        )
    post_movements(
        document_type="Transfer",
        document_id=transfer.pk,
        lines=movement_lines,
        posted_by=posted_by,
    )
    transfer.status = Transfer.Status.POSTED
    transfer.save(update_fields=["status", "total_value", "updated_at"])
    return transfer


@transaction.atomic
def open_stock_take(*, location: Location, started_by: Any) -> StockTake:
    """Open a count, freezing system quantities for every active product."""
    stock_take = StockTake.objects.create(location=location, started_by=started_by)
    balances = StockBalance.objects.filter(location=location).select_related(None)
    StockTakeLine.objects.bulk_create(
        [
            StockTakeLine(
                stock_take=stock_take,
                product_id=balance.product_id,
                system_qty=balance.qty_on_hand,
            )
            for balance in balances
        ]
    )
    return stock_take


@transaction.atomic
def post_stock_take(
    *, stock_take: StockTake, posted_by: Any, skip_approval: bool = False
) -> StockTake:
    """Post counted variances as adjustments, threshold-routed to approval."""
    if stock_take.status == StockTake.Status.POSTED:
        return stock_take
    lines = list(stock_take.lines.filter(counted_qty__isnull=False))
    variant = [line for line in lines if line.variance != 0]
    if not variant:
        stock_take.status = StockTake.Status.POSTED
        stock_take.save(update_fields=["status", "updated_at"])
        return stock_take

    value = lines_value([(line.product_id, abs(line.variance)) for line in variant])
    if not skip_approval and requires_approval(ThresholdConfig.Scope.ADJUSTMENT, value):
        stock_take.status = StockTake.Status.PENDING_APPROVAL
        stock_take.save(update_fields=["status", "updated_at"])
        submit_for_approval(
            subject=stock_take,
            scope=ThresholdConfig.Scope.ADJUSTMENT,
            requested_by=posted_by,
            value=value,
        )
        return stock_take

    post_movements(
        document_type="StockTake",
        document_id=stock_take.pk,
        lines=[
            MovementLine(
                product_id=line.product_id,
                location_id=stock_take.location_id,
                qty_delta=line.variance,
                movement_type=StockMovement.MovementType.STOCKTAKE_ADJ,
            )
            for line in variant
        ],
        posted_by=posted_by,
        allow_negative=True,
    )
    stock_take.status = StockTake.Status.POSTED
    stock_take.save(update_fields=["status", "updated_at"])
    return stock_take

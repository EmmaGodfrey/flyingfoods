"""Procurement service functions for purchase orders, receipts, and reporting."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.events import DomainEvent, get_event_bus
from app.db.models import Product, StockMovement, Supplier, User
from app.db.models.procurement import (
    GoodsReceivedNote,
    GoodsReceivedNoteLineItem,
    PurchaseOrder,
    PurchaseOrderLineItem,
    PurchaseOrderStatus,
)
from app.schemas.procurement import (
    GoodsReceivedNoteCreate,
    GoodsReceivedNoteLineRead,
    GoodsReceivedNoteRead,
    ProcurementOrderReportLine,
    ProcurementOrdersReportResponse,
    PurchaseOrderCreate,
    PurchaseOrderLineItemRead,
    PurchaseOrderListResponse,
    PurchaseOrderRead,
)
from app.schemas.reports import ProcurementSpendLine, ProcurementSpendResponse
from app.services.audit_service import INVENTORY_WRITE_EVENT, create_audit_log


class ProcurementError(Exception):
    pass


class ProcurementNotFoundError(ProcurementError):
    pass


class ProcurementConflictError(ProcurementError):
    pass


class ProcurementValidationError(ProcurementError):
    pass


async def _get_supplier_or_raise(session: AsyncSession, *, branch_id: int, supplier_id: int) -> Supplier:
    stmt = select(Supplier).where(Supplier.id == supplier_id, Supplier.branch_id == branch_id)
    supplier = (await session.execute(stmt)).scalar_one_or_none()
    if supplier is None:
        raise ProcurementValidationError("Supplier not found in current branch")
    return supplier


async def _get_products_by_ids(session: AsyncSession, *, branch_id: int, product_ids: set[int]) -> dict[int, Product]:
    stmt = select(Product).where(Product.branch_id == branch_id, Product.id.in_(product_ids))
    products = (await session.execute(stmt)).scalars().all()
    mapped = {product.id: product for product in products}
    if len(mapped) != len(product_ids):
        raise ProcurementValidationError("One or more products were not found in current branch")
    return mapped


async def _get_purchase_order_or_raise(session: AsyncSession, *, branch_id: int, purchase_order_id: int) -> PurchaseOrder:
    stmt = (
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.line_items), selectinload(PurchaseOrder.receipts))
        .where(PurchaseOrder.id == purchase_order_id, PurchaseOrder.branch_id == branch_id)
    )
    purchase_order = (await session.execute(stmt)).scalar_one_or_none()
    if purchase_order is None:
        raise ProcurementNotFoundError("Purchase order not found")
    return purchase_order


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"))


def _serialize_purchase_order(purchase_order: PurchaseOrder) -> dict[str, Any]:
    return {
        "id": purchase_order.id,
        "branch_id": purchase_order.branch_id,
        "supplier_id": purchase_order.supplier_id,
        "status": purchase_order.status,
        "created_by_user_id": purchase_order.created_by_user_id,
        "submitted_by_user_id": purchase_order.submitted_by_user_id,
        "approved_by_user_id": purchase_order.approved_by_user_id,
        "submitted_at": purchase_order.submitted_at.isoformat() if purchase_order.submitted_at else None,
        "approved_at": purchase_order.approved_at.isoformat() if purchase_order.approved_at else None,
        "received_at": purchase_order.received_at.isoformat() if purchase_order.received_at else None,
        "closed_at": purchase_order.closed_at.isoformat() if purchase_order.closed_at else None,
        "notes": purchase_order.notes,
    }


async def _write_procurement_audit(
    session: AsyncSession,
    *,
    branch_id: int,
    actor_user_id: int | None,
    action: str,
    entity_type: str,
    entity_id: str,
    request_id: str | None,
    before_json: dict[str, Any] | None,
    after_json: dict[str, Any] | None,
    occurred_at: datetime | None = None,
) -> None:
    await create_audit_log(
        session,
        actor_user_id=actor_user_id,
        branch_id=branch_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_json=before_json,
        after_json=after_json,
        request_id=request_id,
        source="api",
        occurred_at=occurred_at or datetime.now(timezone.utc),
    )


async def _publish_stock_receipt_events(
    session: AsyncSession,
    *,
    redis_client: Redis | None,
    branch_id: int,
    actor_user_id: int | None,
    request_id: str | None,
    movements: list[StockMovement],
) -> None:
    event_bus = get_event_bus()
    for movement in movements:
        event = DomainEvent(
            type=INVENTORY_WRITE_EVENT,
            branch_id=branch_id,
            correlation_id=request_id,
            occurred_at=movement.created_at,
            payload={
                "action": f"stock_movement.{movement.movement_type}",
                "entity_type": "stock_movement",
                "entity_id": str(movement.id),
                "actor_user_id": actor_user_id,
                "before_json": None,
                "after_json": {
                    "id": movement.id,
                    "product_id": movement.product_id,
                    "branch_id": movement.branch_id,
                    "qty": str(movement.qty),
                    "movement_type": movement.movement_type,
                    "reference_id": movement.reference_id,
                    "created_by": movement.created_by,
                },
                "source": "api",
            },
        )
        await event_bus.publish(event, context={"session": session, "redis_client": redis_client})


async def _hydrate_purchase_order_read(
    session: AsyncSession,
    purchase_order: PurchaseOrder,
) -> PurchaseOrderRead:
    supplier = await _get_supplier_or_raise(session, branch_id=purchase_order.branch_id, supplier_id=purchase_order.supplier_id)
    product_ids = {line_item.product_id for line_item in purchase_order.line_items}
    products = await _get_products_by_ids(session, branch_id=purchase_order.branch_id, product_ids=product_ids) if product_ids else {}
    return PurchaseOrderRead(
        purchase_order_id=purchase_order.id,
        branch_id=purchase_order.branch_id,
        supplier_id=purchase_order.supplier_id,
        supplier_name=supplier.name,
        status=purchase_order.status,
        notes=purchase_order.notes,
        created_by_user_id=purchase_order.created_by_user_id,
        submitted_by_user_id=purchase_order.submitted_by_user_id,
        approved_by_user_id=purchase_order.approved_by_user_id,
        submitted_at=purchase_order.submitted_at,
        approved_at=purchase_order.approved_at,
        received_at=purchase_order.received_at,
        closed_at=purchase_order.closed_at,
        created_at=purchase_order.created_at,
        line_items=[
            PurchaseOrderLineItemRead(
                line_item_id=line_item.id,
                product_id=line_item.product_id,
                product_name=products[line_item.product_id].name,
                quantity=line_item.quantity,
                unit_price=line_item.unit_price,
                received_quantity=line_item.received_quantity,
            )
            for line_item in purchase_order.line_items
        ],
    )


async def create_purchase_order(
    session: AsyncSession,
    *,
    branch_id: int,
    actor: User,
    payload: PurchaseOrderCreate,
    request_id: str | None,
) -> PurchaseOrderRead:
    supplier = await _get_supplier_or_raise(session, branch_id=branch_id, supplier_id=payload.supplier_id)
    products = await _get_products_by_ids(
        session,
        branch_id=branch_id,
        product_ids={line.product_id for line in payload.line_items},
    )

    purchase_order = PurchaseOrder(
        branch_id=branch_id,
        supplier_id=supplier.id,
        status=PurchaseOrderStatus.draft.value,
        created_by_user_id=actor.id,
        notes=payload.notes,
    )
    session.add(purchase_order)
    await session.flush()

    for line in payload.line_items:
        session.add(
            PurchaseOrderLineItem(
                purchase_order_id=purchase_order.id,
                branch_id=branch_id,
                product_id=line.product_id,
                quantity=line.quantity,
                unit_price=line.unit_price,
                received_quantity=Decimal("0.00"),
            )
        )

    await session.commit()
    purchase_order = await _get_purchase_order_or_raise(session, branch_id=branch_id, purchase_order_id=purchase_order.id)
    await _write_procurement_audit(
        session,
        branch_id=branch_id,
        actor_user_id=actor.id,
        action="purchase_order.create",
        entity_type="purchase_order",
        entity_id=str(purchase_order.id),
        request_id=request_id,
        before_json=None,
        after_json=_serialize_purchase_order(purchase_order),
    )
    return await _hydrate_purchase_order_read(session, purchase_order)


async def list_purchase_orders(
    session: AsyncSession,
    *,
    branch_id: int,
    limit: int,
    offset: int,
    status_filter: str | None,
    supplier_id: int | None,
    date_from: datetime | None,
    date_to: datetime | None,
) -> PurchaseOrderListResponse:
    filters = [PurchaseOrder.branch_id == branch_id]
    if status_filter is not None:
        filters.append(PurchaseOrder.status == status_filter)
    if supplier_id is not None:
        filters.append(PurchaseOrder.supplier_id == supplier_id)
    if date_from is not None:
        filters.append(PurchaseOrder.created_at >= date_from)
    if date_to is not None:
        filters.append(PurchaseOrder.created_at <= date_to)

    count_stmt = select(func.count()).select_from(PurchaseOrder).where(*filters)
    total = int((await session.execute(count_stmt)).scalar_one())

    stmt = (
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.line_items))
        .where(*filters)
        .order_by(PurchaseOrder.created_at.desc(), PurchaseOrder.id.desc())
        .limit(limit)
        .offset(offset)
    )
    orders = (await session.execute(stmt)).scalars().all()
    items = [await _hydrate_purchase_order_read(session, order) for order in orders]
    return PurchaseOrderListResponse(items=items, total=total, limit=limit, offset=offset)


async def submit_purchase_order(
    session: AsyncSession,
    *,
    branch_id: int,
    purchase_order_id: int,
    actor: User,
    request_id: str | None,
) -> PurchaseOrderRead:
    purchase_order = await _get_purchase_order_or_raise(session, branch_id=branch_id, purchase_order_id=purchase_order_id)
    if purchase_order.status != PurchaseOrderStatus.draft.value:
        raise ProcurementConflictError("Only draft purchase orders can be submitted")

    before_json = _serialize_purchase_order(purchase_order)
    purchase_order.status = PurchaseOrderStatus.submitted.value
    purchase_order.submitted_by_user_id = actor.id
    purchase_order.submitted_at = datetime.now(timezone.utc)
    await session.commit()
    purchase_order = await _get_purchase_order_or_raise(session, branch_id=branch_id, purchase_order_id=purchase_order_id)
    await _write_procurement_audit(
        session,
        branch_id=branch_id,
        actor_user_id=actor.id,
        action="purchase_order.submit",
        entity_type="purchase_order",
        entity_id=str(purchase_order.id),
        request_id=request_id,
        before_json=before_json,
        after_json=_serialize_purchase_order(purchase_order),
    )
    return await _hydrate_purchase_order_read(session, purchase_order)


async def approve_purchase_order(
    session: AsyncSession,
    *,
    branch_id: int,
    purchase_order_id: int,
    actor: User,
    request_id: str | None,
) -> PurchaseOrderRead:
    purchase_order = await _get_purchase_order_or_raise(session, branch_id=branch_id, purchase_order_id=purchase_order_id)
    if purchase_order.status != PurchaseOrderStatus.submitted.value:
        raise ProcurementConflictError("Only submitted purchase orders can be approved")

    before_json = _serialize_purchase_order(purchase_order)
    purchase_order.status = PurchaseOrderStatus.approved.value
    purchase_order.approved_by_user_id = actor.id
    purchase_order.approved_at = datetime.now(timezone.utc)
    await session.commit()
    purchase_order = await _get_purchase_order_or_raise(session, branch_id=branch_id, purchase_order_id=purchase_order_id)
    await _write_procurement_audit(
        session,
        branch_id=branch_id,
        actor_user_id=actor.id,
        action="purchase_order.approve",
        entity_type="purchase_order",
        entity_id=str(purchase_order.id),
        request_id=request_id,
        before_json=before_json,
        after_json=_serialize_purchase_order(purchase_order),
    )
    return await _hydrate_purchase_order_read(session, purchase_order)


async def create_goods_received_note(
    session: AsyncSession,
    *,
    branch_id: int,
    actor: User,
    payload: GoodsReceivedNoteCreate,
    request_id: str | None,
    redis_client: Redis | None,
) -> GoodsReceivedNoteRead:
    purchase_order = await _get_purchase_order_or_raise(session, branch_id=branch_id, purchase_order_id=payload.purchase_order_id)
    if purchase_order.status not in {PurchaseOrderStatus.approved.value, PurchaseOrderStatus.received.value}:
        raise ProcurementConflictError("Only approved or partially received purchase orders can receive goods")

    line_item_map = {line_item.id: line_item for line_item in purchase_order.line_items}
    product_ids = {line_item.product_id for line_item in purchase_order.line_items}
    products = await _get_products_by_ids(session, branch_id=branch_id, product_ids=product_ids)

    receipt = GoodsReceivedNote(
        purchase_order_id=purchase_order.id,
        branch_id=branch_id,
        received_by_user_id=actor.id,
        reference=payload.reference,
        notes=payload.notes,
    )
    session.add(receipt)
    await session.flush()

    stock_movements: list[StockMovement] = []
    receipt_lines: list[GoodsReceivedNoteLineItem] = []
    for line in payload.line_items:
        purchase_order_line = line_item_map.get(line.purchase_order_line_item_id)
        if purchase_order_line is None:
            raise ProcurementValidationError("Purchase order line item not found")
        new_received_total = purchase_order_line.received_quantity + line.quantity_received
        if new_received_total > purchase_order_line.quantity:
            raise ProcurementValidationError("Received quantity exceeds ordered quantity")

        purchase_order_line.received_quantity = new_received_total
        receipt_line = GoodsReceivedNoteLineItem(
            goods_received_note_id=receipt.id,
            purchase_order_line_item_id=purchase_order_line.id,
            branch_id=branch_id,
            product_id=purchase_order_line.product_id,
            quantity_received=line.quantity_received,
        )
        receipt_lines.append(receipt_line)
        session.add(receipt_line)

        movement = StockMovement(
            product_id=purchase_order_line.product_id,
            branch_id=branch_id,
            qty=line.quantity_received,
            movement_type="receive",
            reference_id=f"grn:{receipt.id}",
            created_by=actor.id,
            created_at=datetime.now(timezone.utc),
        )
        stock_movements.append(movement)
        session.add(movement)

    now = datetime.now(timezone.utc)
    purchase_order.received_at = now
    if all(line_item.received_quantity >= line_item.quantity for line_item in purchase_order.line_items):
        purchase_order.status = PurchaseOrderStatus.closed.value
        purchase_order.closed_at = now
    else:
        purchase_order.status = PurchaseOrderStatus.received.value

    await session.commit()
    for movement in stock_movements:
        await session.refresh(movement)

    await _write_procurement_audit(
        session,
        branch_id=branch_id,
        actor_user_id=actor.id,
        action="goods_received_note.create",
        entity_type="goods_received_note",
        entity_id=str(receipt.id),
        request_id=request_id,
        before_json=None,
        after_json={
            "id": receipt.id,
            "purchase_order_id": purchase_order.id,
            "reference": receipt.reference,
            "status_after_receipt": purchase_order.status,
        },
    )
    await _publish_stock_receipt_events(
        session,
        redis_client=redis_client,
        branch_id=branch_id,
        actor_user_id=actor.id,
        request_id=request_id,
        movements=stock_movements,
    )

    return GoodsReceivedNoteRead(
        goods_received_note_id=receipt.id,
        purchase_order_id=purchase_order.id,
        branch_id=branch_id,
        status_after_receipt=purchase_order.status,
        reference=receipt.reference,
        notes=receipt.notes,
        received_by_user_id=receipt.received_by_user_id,
        created_at=receipt.created_at,
        line_items=[
            GoodsReceivedNoteLineRead(
                goods_received_note_line_item_id=receipt_line.id,
                purchase_order_line_item_id=receipt_line.purchase_order_line_item_id,
                product_id=receipt_line.product_id,
                product_name=products[receipt_line.product_id].name,
                quantity_received=receipt_line.quantity_received,
            )
            for receipt_line in receipt_lines
        ],
    )


async def get_procurement_orders_report(
    session: AsyncSession,
    *,
    branch_id: int,
    limit: int,
    offset: int,
    status_filter: str | None,
    supplier_id: int | None,
    date_from: datetime | None,
    date_to: datetime | None,
) -> ProcurementOrdersReportResponse:
    filters = [PurchaseOrder.branch_id == branch_id]
    if status_filter is not None:
        filters.append(PurchaseOrder.status == status_filter)
    if supplier_id is not None:
        filters.append(PurchaseOrder.supplier_id == supplier_id)
    if date_from is not None:
        filters.append(PurchaseOrder.created_at >= date_from)
    if date_to is not None:
        filters.append(PurchaseOrder.created_at <= date_to)

    count_stmt = select(func.count()).select_from(PurchaseOrder).where(*filters)
    total = int((await session.execute(count_stmt)).scalar_one())

    stmt = (
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.line_items))
        .where(*filters)
        .order_by(PurchaseOrder.created_at.desc(), PurchaseOrder.id.desc())
        .limit(limit)
        .offset(offset)
    )
    orders = (await session.execute(stmt)).scalars().all()
    supplier_ids = {order.supplier_id for order in orders}
    suppliers = {}
    if supplier_ids:
        supplier_stmt = select(Supplier).where(Supplier.branch_id == branch_id, Supplier.id.in_(supplier_ids))
        suppliers = {supplier.id: supplier for supplier in (await session.execute(supplier_stmt)).scalars().all()}

    items = []
    for order in orders:
        ordered_total = sum((_money(line.quantity * line.unit_price) for line in order.line_items), Decimal("0.00"))
        received_total = sum((_money(line.received_quantity * line.unit_price) for line in order.line_items), Decimal("0.00"))
        items.append(
            ProcurementOrderReportLine(
                purchase_order_id=order.id,
                created_at=order.created_at,
                supplier_id=order.supplier_id,
                supplier_name=suppliers[order.supplier_id].name,
                status=order.status,
                line_count=len(order.line_items),
                ordered_total=_money(ordered_total),
                received_total=_money(received_total),
            )
        )

    return ProcurementOrdersReportResponse(
        branch_id=branch_id,
        total=total,
        limit=limit,
        offset=offset,
        status=status_filter,
        supplier_id=supplier_id,
        date_from=date_from,
        date_to=date_to,
        items=items,
    )


async def get_procurement_spend_report_week6(
    session: AsyncSession,
    *,
    branch_id: int,
    date_from: datetime | None,
    date_to: datetime | None,
) -> ProcurementSpendResponse:
    stmt = (
        select(
            GoodsReceivedNote.created_at,
            PurchaseOrder.supplier_id,
            Supplier.name,
            PurchaseOrderLineItem.unit_price,
            GoodsReceivedNoteLineItem.quantity_received,
        )
        .join(PurchaseOrder, PurchaseOrder.id == GoodsReceivedNote.purchase_order_id)
        .join(Supplier, Supplier.id == PurchaseOrder.supplier_id)
        .join(GoodsReceivedNoteLineItem, GoodsReceivedNoteLineItem.goods_received_note_id == GoodsReceivedNote.id)
        .join(PurchaseOrderLineItem, PurchaseOrderLineItem.id == GoodsReceivedNoteLineItem.purchase_order_line_item_id)
        .where(GoodsReceivedNote.branch_id == branch_id)
        .order_by(GoodsReceivedNote.created_at.asc(), GoodsReceivedNote.id.asc())
    )
    if date_from is not None:
        stmt = stmt.where(GoodsReceivedNote.created_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(GoodsReceivedNote.created_at <= date_to)

    rows = (await session.execute(stmt)).all()
    aggregates: defaultdict[tuple[str, int, str], Decimal] = defaultdict(lambda: Decimal("0.00"))
    for row in rows:
        month = row.created_at.strftime("%Y-%m")
        spend = _money(row.unit_price * row.quantity_received)
        aggregates[(month, row.supplier_id, row.name)] += spend

    report_rows = [
        ProcurementSpendLine(
            month=month,
            supplier_id=supplier_id,
            supplier_name=supplier_name,
            total_spend=_money(total_spend),
        )
        for (month, supplier_id, supplier_name), total_spend in sorted(aggregates.items(), key=lambda item: item[0])
    ]
    return ProcurementSpendResponse(branch_id=branch_id, date_from=date_from, date_to=date_to, rows=report_rows)

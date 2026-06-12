"""Reporting service functions for sales, inventory, and procurement analytics."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from decimal import Decimal
import json
from typing import Any

from celery.result import AsyncResult
from redis.asyncio import Redis
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_app import celery_app
from app.db.models import Product, Sale, SaleLineItem, StockMovement
from app.db.models.procurement import GoodsReceivedNote, GoodsReceivedNoteLineItem, PurchaseOrder, PurchaseOrderLineItem
from app.db.models.supplier import Supplier
from app.schemas.reports import (
    InventoryMovementReportLine,
    InventoryMovementReportResponse,
    InventoryValuationLine,
    InventoryValuationResponse,
    ProcurementSpendLine,
    ProcurementSpendResponse,
    ReportTaskEnqueueResponse,
    ReportTaskStatus,
    ReportTaskStatusResponse,
    SalesReportLine,
    SalesReportResponse,
    SalesReportTotals,
)
from app.tasks.report_tasks import build_procurement_spend_report_task

MONEY_QUANTUM = Decimal("0.01")
_REPORT_TASK_META_FALLBACK: dict[str, dict[str, Any]] = {}
_PROCUREMENT_SPEND_REPORT_TYPE = "procurement_spend"


class ReportTaskNotFoundError(Exception):
    pass


def _quantize_money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANTUM)


def _report_task_meta_key(task_id: str) -> str:
    return f"reports:task:{task_id}"


async def _store_report_task_meta(redis_client: Redis | None, task_id: str, meta: dict[str, Any]) -> None:
    _REPORT_TASK_META_FALLBACK[task_id] = meta
    if redis_client is None:
        return
    await redis_client.setex(_report_task_meta_key(task_id), 86400, json.dumps(meta))


async def _load_report_task_meta(redis_client: Redis | None, task_id: str) -> dict[str, Any] | None:
    if redis_client is not None:
        raw = await redis_client.get(_report_task_meta_key(task_id))
        if raw:
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            return json.loads(raw)
    return _REPORT_TASK_META_FALLBACK.get(task_id)


async def get_sales_report(
    session: AsyncSession,
    *,
    branch_id: int,
    date_from: datetime | None,
    date_to: datetime | None,
    cashier_user_id: int | None,
    product_id: int | None,
    payment_method: str | None,
) -> SalesReportResponse:
    filters = [Sale.branch_id == branch_id, SaleLineItem.branch_id == branch_id]
    if date_from is not None:
        filters.append(Sale.created_at >= date_from)
    if date_to is not None:
        filters.append(Sale.created_at <= date_to)
    if cashier_user_id is not None:
        filters.append(Sale.cashier_user_id == cashier_user_id)
    if product_id is not None:
        filters.append(SaleLineItem.product_id == product_id)
    if payment_method is not None:
        filters.append(Sale.payment_method == payment_method)

    stmt = (
        select(
            Sale.id,
            Sale.created_at,
            Sale.cashier_user_id,
            Sale.payment_method,
            SaleLineItem.product_id,
            Product.name,
            SaleLineItem.quantity,
            SaleLineItem.unit_price,
            SaleLineItem.line_total,
        )
        .join(SaleLineItem, SaleLineItem.sale_id == Sale.id)
        .join(Product, Product.id == SaleLineItem.product_id)
        .where(and_(*filters))
        .order_by(Sale.created_at.desc(), Sale.id.desc(), SaleLineItem.id.asc())
    )

    rows = (await session.execute(stmt)).all()
    lines = [
        SalesReportLine(
            sale_id=row.id,
            sold_at=row.created_at,
            cashier_user_id=row.cashier_user_id,
            payment_method=row.payment_method,
            product_id=row.product_id,
            product_name=row.name,
            quantity=row.quantity,
            unit_price=row.unit_price,
            line_total=row.line_total,
        )
        for row in rows
    ]

    sale_ids = {line.sale_id for line in lines}
    quantity_total = sum((line.quantity for line in lines), Decimal("0"))
    gross_total = sum((line.line_total for line in lines), Decimal("0"))

    return SalesReportResponse(
        branch_id=branch_id,
        date_from=date_from,
        date_to=date_to,
        payment_method=payment_method,
        cashier_user_id=cashier_user_id,
        product_id=product_id,
        totals=SalesReportTotals(
            sale_count=len(sale_ids),
            line_count=len(lines),
            quantity_total=_quantize_money(quantity_total),
            gross_total=_quantize_money(gross_total),
        ),
        lines=lines,
    )


async def get_inventory_valuation_report(session: AsyncSession, *, branch_id: int) -> InventoryValuationResponse:
    stock_subquery = (
        select(
            StockMovement.product_id.label("product_id"),
            func.coalesce(func.sum(StockMovement.qty), Decimal("0")).label("computed_stock"),
        )
        .where(StockMovement.branch_id == branch_id)
        .group_by(StockMovement.product_id)
        .subquery()
    )

    stmt = (
        select(
            Product.id,
            Product.name,
            Product.supplier_id,
            Product.cost_price,
            func.coalesce(stock_subquery.c.computed_stock, Decimal("0")).label("computed_stock"),
        )
        .outerjoin(stock_subquery, stock_subquery.c.product_id == Product.id)
        .where(Product.branch_id == branch_id)
        .order_by(Product.id.asc())
    )

    rows = (await session.execute(stmt)).all()
    items: list[InventoryValuationLine] = []
    total_valuation = Decimal("0")

    for row in rows:
        valuation = _quantize_money(Decimal(row.computed_stock) * Decimal(row.cost_price))
        total_valuation += valuation
        items.append(
            InventoryValuationLine(
                product_id=row.id,
                product_name=row.name,
                supplier_id=row.supplier_id,
                computed_stock=_quantize_money(Decimal(row.computed_stock)),
                cost_price=_quantize_money(Decimal(row.cost_price)),
                valuation=valuation,
            )
        )

    return InventoryValuationResponse(
        branch_id=branch_id,
        total_valuation=_quantize_money(total_valuation),
        items=items,
    )


async def get_inventory_movements_report(
    session: AsyncSession,
    *,
    branch_id: int,
    limit: int,
    offset: int,
    movement_type: str | None,
    product_id: int | None,
    date_from: datetime | None,
    date_to: datetime | None,
) -> InventoryMovementReportResponse:
    filters = [StockMovement.branch_id == branch_id]
    if movement_type is not None:
        filters.append(StockMovement.movement_type == movement_type)
    if product_id is not None:
        filters.append(StockMovement.product_id == product_id)
    if date_from is not None:
        filters.append(StockMovement.created_at >= date_from)
    if date_to is not None:
        filters.append(StockMovement.created_at <= date_to)

    count_stmt = select(func.count(StockMovement.id)).where(and_(*filters))
    total = int((await session.execute(count_stmt)).scalar_one() or 0)

    stmt = (
        select(
            StockMovement.id,
            StockMovement.created_at,
            StockMovement.movement_type,
            StockMovement.product_id,
            Product.name,
            StockMovement.qty,
            StockMovement.reference_id,
            StockMovement.created_by,
        )
        .join(Product, Product.id == StockMovement.product_id)
        .where(and_(*filters))
        .order_by(StockMovement.created_at.desc(), StockMovement.id.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()

    items = [
        InventoryMovementReportLine(
            movement_id=row.id,
            occurred_at=row.created_at,
            movement_type=row.movement_type,
            product_id=row.product_id,
            product_name=row.name,
            qty=row.qty,
            reference_id=row.reference_id,
            created_by=row.created_by,
        )
        for row in rows
    ]

    return InventoryMovementReportResponse(
        branch_id=branch_id,
        total=total,
        limit=limit,
        offset=offset,
        movement_type=movement_type,
        product_id=product_id,
        date_from=date_from,
        date_to=date_to,
        items=items,
    )


async def get_procurement_spend_report(
    session: AsyncSession,
    *,
    branch_id: int,
    date_from: datetime | None,
    date_to: datetime | None,
) -> ProcurementSpendResponse:
    filters = [GoodsReceivedNote.branch_id == branch_id]
    if date_from is not None:
        filters.append(GoodsReceivedNote.created_at >= date_from)
    if date_to is not None:
        filters.append(GoodsReceivedNote.created_at <= date_to)

    stmt = (
        select(
            GoodsReceivedNote.created_at,
            PurchaseOrder.supplier_id,
            Supplier.name,
            GoodsReceivedNoteLineItem.quantity_received,
            PurchaseOrderLineItem.unit_price,
        )
        .join(PurchaseOrder, PurchaseOrder.id == GoodsReceivedNote.purchase_order_id)
        .join(Supplier, Supplier.id == PurchaseOrder.supplier_id)
        .join(GoodsReceivedNoteLineItem, GoodsReceivedNoteLineItem.goods_received_note_id == GoodsReceivedNote.id)
        .join(PurchaseOrderLineItem, PurchaseOrderLineItem.id == GoodsReceivedNoteLineItem.purchase_order_line_item_id)
        .where(and_(*filters))
    )
    rows = (await session.execute(stmt)).all()

    aggregates: dict[tuple[str, int | None, str], Decimal] = defaultdict(lambda: Decimal("0"))
    for row in rows:
        month = row.created_at.strftime("%Y-%m")
        supplier_id = row.supplier_id
        supplier_name = row.name or "Unassigned"
        spend = Decimal(row.quantity_received) * Decimal(row.unit_price)
        aggregates[(month, supplier_id, supplier_name)] += spend

    report_rows = [
        ProcurementSpendLine(
            month=month,
            supplier_id=supplier_id,
            supplier_name=supplier_name,
            total_spend=_quantize_money(total_spend),
        )
        for (month, supplier_id, supplier_name), total_spend in sorted(aggregates.items(), key=lambda item: item[0])
    ]

    return ProcurementSpendResponse(
        branch_id=branch_id,
        date_from=date_from,
        date_to=date_to,
        rows=report_rows,
    )


async def enqueue_procurement_spend_report_task(
    session: AsyncSession,
    *,
    branch_id: int,
    date_from: datetime | None,
    date_to: datetime | None,
    request_id: str | None,
    redis_client: Redis | None = None,
) -> ReportTaskEnqueueResponse:
    report = await get_procurement_spend_report(
        session,
        branch_id=branch_id,
        date_from=date_from,
        date_to=date_to,
    )

    task = build_procurement_spend_report_task.delay(
        branch_id=branch_id,
        rows=[row.model_dump(mode="json") for row in report.rows],
        request_id=request_id,
    )

    await _store_report_task_meta(
        redis_client,
        task.id,
        {
            "branch_id": branch_id,
            "report_type": _PROCUREMENT_SPEND_REPORT_TYPE,
            "date_from": date_from.isoformat() if date_from else None,
            "date_to": date_to.isoformat() if date_to else None,
        },
    )

    return ReportTaskEnqueueResponse(
        task_id=task.id,
        branch_id=branch_id,
        status=ReportTaskStatus.queued,
        report_type=_PROCUREMENT_SPEND_REPORT_TYPE,
    )


async def get_report_task_status(
    *,
    branch_id: int,
    task_id: str,
    redis_client: Redis | None = None,
) -> ReportTaskStatusResponse:
    meta = await _load_report_task_meta(redis_client, task_id)
    if meta is None:
        raise ReportTaskNotFoundError("Report task not found")
    if int(meta["branch_id"]) != branch_id:
        raise ReportTaskNotFoundError("Report task not found")

    result = AsyncResult(task_id, app=celery_app)
    if result.state in {"PENDING", "RECEIVED"}:
        status = ReportTaskStatus.queued
    elif result.state in {"STARTED", "RETRY"}:
        status = ReportTaskStatus.running
    elif result.state == "SUCCESS":
        status = ReportTaskStatus.succeeded
    elif result.state == "FAILURE":
        status = ReportTaskStatus.failed
    else:
        status = ReportTaskStatus.running

    payload: ProcurementSpendResponse | None = None
    error: str | None = None

    if status == ReportTaskStatus.succeeded:
        data = result.result or {}
        rows = [ProcurementSpendLine.model_validate(row) for row in data.get("rows", [])]
        payload = ProcurementSpendResponse(
            branch_id=branch_id,
            date_from=datetime.fromisoformat(meta["date_from"]) if meta.get("date_from") else None,
            date_to=datetime.fromisoformat(meta["date_to"]) if meta.get("date_to") else None,
            rows=rows,
        )
    elif status == ReportTaskStatus.failed:
        error = str(result.result)

    return ReportTaskStatusResponse(
        task_id=task_id,
        branch_id=branch_id,
        status=status,
        report_type=str(meta["report_type"]),
        result=payload,
        error=error,
    )

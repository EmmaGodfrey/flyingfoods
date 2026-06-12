"""Sales service with transactional checkout and BOM-aware stock validation."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from decimal import Decimal
import json
from time import perf_counter
from typing import Any, Protocol

from celery.result import AsyncResult
from redis.asyncio import Redis
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.celery_app import celery_app
from app.core.events import DomainEvent, get_event_bus
from app.core.observability import increment_counter, log_event, measure_elapsed_ms, observe_histogram_ms
from app.db.models import BillOfMaterial, Product, Sale, SaleLineItem, StockMovement, User
from app.schemas.sales import (
    DailySalesSummary,
    PaymentMethod,
    PaymentProvider,
    PaymentStatus,
    ReconciliationJobStatus,
    SaleCreate,
    SaleLineItemRead,
    SalePaymentIntentRequest,
    SalePaymentIntentResult,
    SalePaymentReconcileJobEnqueueResult,
    SalePaymentReconcileJobStatusResult,
    SalePaymentReconcileRequest,
    SalePaymentReconcileResult,
    SalePaymentTenderAuthorization,
    SaleReceipt,
    SaleRefundResult,
    SaleTenderCreate,
    SaleVoidResult,
)
from app.services.audit_service import INVENTORY_WRITE_EVENT
from app.services.search_indexing import index_invoice_document
from app.tasks.sales_tasks import reconcile_sale_payment_task

MONEY_QUANTUM = Decimal("0.01")


class SaleValidationError(Exception):
    pass


class SaleProductNotFoundError(Exception):
    pass


class SaleNotFoundError(Exception):
    pass


class PaymentProviderError(Exception):
    pass


class ReconciliationJobNotFoundError(Exception):
    pass


@dataclass(slots=True)
class _ResolvedItem:
    product: Product
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal


@dataclass(slots=True)
class _ProviderAuthorization:
    provider: PaymentProvider
    provider_reference: str
    amount: Decimal
    status: PaymentStatus


@dataclass(slots=True)
class _ProviderReconciliation:
    provider: PaymentProvider
    provider_reference: str
    amount: Decimal
    status: PaymentStatus
    reconciled_at: datetime


class _PaymentProviderGateway(Protocol):
    async def authorize_tender(
        self,
        *,
        sale_id: int,
        branch_id: int,
        tender_index: int,
        payment_method: PaymentMethod,
        amount: Decimal,
        request_id: str | None,
    ) -> _ProviderAuthorization: ...

    async def reconcile_reference(
        self,
        *,
        sale_id: int,
        branch_id: int,
        provider_reference: str,
        amount: Decimal,
        request_id: str | None,
    ) -> _ProviderReconciliation: ...


class _SimulatedPaymentProvider:
    async def authorize_tender(
        self,
        *,
        sale_id: int,
        branch_id: int,
        tender_index: int,
        payment_method: PaymentMethod,
        amount: Decimal,
        request_id: str | None,
    ) -> _ProviderAuthorization:
        cents = int(_quantize_money(amount) * 100)
        request_suffix = request_id or "no-request-id"
        provider_reference = f"sim-{branch_id}-{sale_id}-{tender_index}-{cents}-{request_suffix}"
        return _ProviderAuthorization(
            provider=PaymentProvider.simulated,
            provider_reference=provider_reference,
            amount=_quantize_money(amount),
            status=PaymentStatus.authorized,
        )

    async def reconcile_reference(
        self,
        *,
        sale_id: int,
        branch_id: int,
        provider_reference: str,
        amount: Decimal,
        request_id: str | None,
    ) -> _ProviderReconciliation:
        prefix = f"sim-{branch_id}-{sale_id}-"
        if not provider_reference.startswith(prefix):
            raise PaymentProviderError("Provider reference does not match sale context")
        return _ProviderReconciliation(
            provider=PaymentProvider.simulated,
            provider_reference=provider_reference,
            amount=_quantize_money(amount),
            status=PaymentStatus.reconciled,
            reconciled_at=datetime.now(timezone.utc),
        )


def _payment_provider_for(provider: PaymentProvider) -> _PaymentProviderGateway:
    if provider == PaymentProvider.simulated:
        return _SimulatedPaymentProvider()
    raise PaymentProviderError("Unsupported payment provider")


_RECONCILIATION_META_FALLBACK: dict[str, dict[str, Any]] = {}


def _digital_tender_total_from_sale(sale: Sale) -> Decimal:
    payment_tenders = sale.payment_tenders or [{"payment_method": sale.payment_method, "amount": str(sale.total)}]
    digital_total = Decimal("0")
    for tender in payment_tenders:
        method = PaymentMethod(tender["payment_method"])
        if method in {PaymentMethod.card, PaymentMethod.mobile}:
            digital_total += Decimal(tender["amount"])
    digital_total = _quantize_money(digital_total)
    if digital_total <= Decimal("0"):
        raise SaleValidationError("Sale has no provider-eligible tenders")
    return digital_total


def _reconciliation_meta_key(job_id: str) -> str:
    return f"sales:payment:reconcile:job:{job_id}"


async def _store_reconciliation_meta(redis_client: Redis | None, job_id: str, meta: dict[str, Any]) -> None:
    _RECONCILIATION_META_FALLBACK[job_id] = meta
    if redis_client is None:
        return
    await redis_client.setex(_reconciliation_meta_key(job_id), 86400, json.dumps(meta))


async def _load_reconciliation_meta(redis_client: Redis | None, job_id: str) -> dict[str, Any] | None:
    if redis_client is not None:
        raw = await redis_client.get(_reconciliation_meta_key(job_id))
        if raw:
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            return json.loads(raw)
    return _RECONCILIATION_META_FALLBACK.get(job_id)


def _serialize_decimal(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    return value


def _serialize_sale(sale: Sale) -> dict[str, Any]:
    return {
        "id": sale.id,
        "branch_id": sale.branch_id,
        "cashier_user_id": sale.cashier_user_id,
        "payment_method": sale.payment_method,
        "subtotal": _serialize_decimal(sale.subtotal),
        "tax_amount": _serialize_decimal(sale.tax_amount),
        "discount_amount": _serialize_decimal(sale.discount_amount),
        "total": _serialize_decimal(sale.total),
        "payment_tenders": sale.payment_tenders,
    }


def _normalize_items(payload: SaleCreate) -> dict[int, Decimal]:
    by_product: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    for item in payload.items:
        by_product[item.product_id] += item.quantity
    return by_product


def _quantize_money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANTUM)


def _resolve_payment_tenders(payload: SaleCreate, total: Decimal) -> list[dict[str, str]]:
    if payload.payment_method == "split":
        if not payload.split_tenders:
            raise SaleValidationError("Split tenders are required for split payments")

        tender_total = sum((tender.amount for tender in payload.split_tenders), Decimal("0"))
        tender_total = _quantize_money(tender_total)
        if tender_total != total:
            raise SaleValidationError("Split tenders must sum to total")

        return [
            {"payment_method": tender.payment_method.value, "amount": str(_quantize_money(tender.amount))}
            for tender in payload.split_tenders
        ]

    if payload.split_tenders:
        raise SaleValidationError("Split tenders are only allowed for split payments")

    return [{"payment_method": payload.payment_method.value, "amount": str(total)}]


async def _publish_sale_write(
    *,
    session: AsyncSession,
    redis_client: Redis | None,
    branch_id: int,
    sale: Sale,
    action: str,
    before_json: dict[str, Any] | None,
    after_json: dict[str, Any] | None,
    actor_user_id: int | None,
    request_id: str | None,
) -> None:
    increment_counter(
        "inventory_write_publish_total",
        action=action,
        entity_type="sale",
        branch_id=branch_id,
    )
    log_event(
        "sales.write.publish",
        request_id=request_id,
        correlation_id=request_id,
        branch_id=branch_id,
        actor_user_id=actor_user_id,
        sale_id=sale.id,
    )

    event = DomainEvent(
        type=INVENTORY_WRITE_EVENT,
        branch_id=branch_id,
        correlation_id=request_id,
        occurred_at=datetime.now(timezone.utc),
        payload={
            "action": action,
            "entity_type": "sale",
            "entity_id": str(sale.id),
            "actor_user_id": actor_user_id,
            "before_json": before_json,
            "after_json": after_json,
            "source": "api",
        },
    )
    await get_event_bus().publish(event, context={"session": session, "redis_client": redis_client})


def _receipt_from_sale(sale: Sale) -> SaleReceipt:
    payment_tenders = sale.payment_tenders or [{"payment_method": sale.payment_method, "amount": str(sale.total)}]
    line_items = [
        SaleLineItemRead(
            product_id=line.product_id,
            quantity=line.quantity,
            unit_price=line.unit_price,
            line_total=line.line_total,
        )
        for line in sale.line_items
    ]
    line_items.sort(key=lambda item: item.product_id)

    return SaleReceipt(
        sale_id=sale.id,
        branch_id=sale.branch_id,
        cashier_user_id=sale.cashier_user_id,
        payment_method=sale.payment_method,
        subtotal=sale.subtotal,
        tax_amount=sale.tax_amount,
        discount_amount=sale.discount_amount,
        total=sale.total,
        payment_tenders=[SaleTenderCreate.model_validate(tender) for tender in payment_tenders],
        created_at=sale.created_at,
        line_items=line_items,
    )


def _void_result_from_sale(sale: Sale) -> SaleVoidResult:
    return SaleVoidResult(
        sale_id=sale.id,
        status=sale.status,
        voided_at=sale.voided_at or datetime.now(timezone.utc),
        voided_by_user_id=sale.voided_by_user_id,
        reason=sale.void_reason,
    )


def _refund_result_from_sale(sale: Sale) -> SaleRefundResult:
    return SaleRefundResult(
        sale_id=sale.id,
        status=sale.status,
        refunded_at=sale.refunded_at or datetime.now(timezone.utc),
        refunded_by_user_id=sale.refunded_by_user_id,
        reason=sale.refund_reason,
    )


async def _resolve_products(
    session: AsyncSession,
    *,
    branch_id: int,
    product_quantities: dict[int, Decimal],
) -> dict[int, Product]:
    product_ids = list(product_quantities.keys())
    stmt = select(Product).where(
        Product.id.in_(product_ids),
        Product.branch_id == branch_id,
        Product.is_active.is_(True),
    )
    products = (await session.execute(stmt)).scalars().all()
    by_id = {product.id: product for product in products}

    missing = [product_id for product_id in product_ids if product_id not in by_id]
    if missing:
        raise SaleProductNotFoundError("Product not found in current branch")

    return by_id


async def _resolve_boms(
    session: AsyncSession,
    *,
    branch_id: int,
    product_ids: Iterable[int],
) -> dict[int, list[BillOfMaterial]]:
    ids = list(product_ids)
    if not ids:
        return {}

    stmt = select(BillOfMaterial).where(BillOfMaterial.branch_id == branch_id, BillOfMaterial.product_id.in_(ids))
    rows = (await session.execute(stmt)).scalars().all()

    by_product: dict[int, list[BillOfMaterial]] = defaultdict(list)
    for row in rows:
        by_product[row.product_id].append(row)
    return by_product


async def _validate_stock(
    session: AsyncSession,
    *,
    branch_id: int,
    required_deltas: dict[int, Decimal],
) -> None:
    if not required_deltas:
        return

    tracked_ids = list(required_deltas.keys())
    stock_stmt = (
        select(StockMovement.product_id, func.coalesce(func.sum(StockMovement.qty), 0).label("computed_stock"))
        .where(StockMovement.branch_id == branch_id, StockMovement.product_id.in_(tracked_ids))
        .group_by(StockMovement.product_id)
    )
    stock_rows = (await session.execute(stock_stmt)).all()
    available_by_product = {row.product_id: row.computed_stock for row in stock_rows}

    product_stmt = select(Product.id, Product.name).where(Product.id.in_(tracked_ids), Product.branch_id == branch_id)
    product_rows = (await session.execute(product_stmt)).all()
    names_by_id = {row.id: row.name for row in product_rows}

    for product_id, delta in required_deltas.items():
        available = available_by_product.get(product_id, Decimal("0"))
        if available + delta < 0:
            product_name = names_by_id.get(product_id, f"product:{product_id}")
            raise SaleValidationError(f"Insufficient stock for {product_name}")


async def create_sale(
    session: AsyncSession,
    *,
    branch_id: int,
    actor: User,
    payload: SaleCreate,
    request_id: str | None,
    redis_client: Redis | None = None,
) -> SaleReceipt:
    started = perf_counter()
    increment_counter("sales_create_requests_total", branch_id=branch_id, role=actor.role)

    product_quantities = _normalize_items(payload)
    products_by_id = await _resolve_products(session, branch_id=branch_id, product_quantities=product_quantities)
    boms_by_product = await _resolve_boms(session, branch_id=branch_id, product_ids=products_by_id.keys())

    required_stock_deltas: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    resolved_items: list[_ResolvedItem] = []

    for product_id, quantity in product_quantities.items():
        product = products_by_id[product_id]
        unit_price = product.selling_price
        line_total = (unit_price * quantity).quantize(MONEY_QUANTUM)
        resolved_items.append(_ResolvedItem(product=product, quantity=quantity, unit_price=unit_price, line_total=line_total))

        bom_rows = boms_by_product.get(product_id, [])
        if bom_rows:
            for bom in bom_rows:
                required_stock_deltas[bom.ingredient_id] -= bom.quantity * quantity
        else:
            required_stock_deltas[product_id] -= quantity

    await _validate_stock(session, branch_id=branch_id, required_deltas=required_stock_deltas)

    subtotal = _quantize_money(sum((item.line_total for item in resolved_items), Decimal("0")))
    tax_amount = _quantize_money(payload.tax_amount)
    discount_amount = _quantize_money(payload.discount_amount)
    total = _quantize_money(subtotal + tax_amount - discount_amount)
    if total < Decimal("0"):
        raise SaleValidationError("Sale total cannot be negative")

    payment_tenders = _resolve_payment_tenders(payload, total)

    sale = Sale(
        branch_id=branch_id,
        cashier_user_id=actor.id,
        payment_method=payload.payment_method.value,
        subtotal=subtotal,
        tax_amount=tax_amount,
        discount_amount=discount_amount,
        total=total,
        payment_tenders=payment_tenders,
    )
    session.add(sale)
    await session.flush()

    for item in resolved_items:
        session.add(
            SaleLineItem(
                sale_id=sale.id,
                branch_id=branch_id,
                product_id=item.product.id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                line_total=item.line_total,
            )
        )

    for product_id, qty_delta in required_stock_deltas.items():
        session.add(
            StockMovement(
                product_id=product_id,
                branch_id=branch_id,
                qty=qty_delta,
                movement_type="sale",
                reference_id=f"sale:{sale.id}",
                created_by=actor.id,
            )
        )

    await session.commit()

    sale_stmt = (
        select(Sale)
        .where(Sale.id == sale.id, Sale.branch_id == branch_id)
        .options(selectinload(Sale.line_items))
    )
    saved_sale = (await session.execute(sale_stmt)).scalar_one()

    await _publish_sale_write(
        session=session,
        redis_client=redis_client,
        branch_id=branch_id,
        sale=saved_sale,
        action="sale.create",
        before_json=None,
        after_json=_serialize_sale(saved_sale),
        actor_user_id=actor.id,
        request_id=request_id,
    )
    index_invoice_document(
        sale_id=saved_sale.id,
        branch_id=saved_sale.branch_id,
        payment_method=saved_sale.payment_method,
        total=saved_sale.total,
        created_at=saved_sale.created_at,
    )

    duration_ms = measure_elapsed_ms(started)
    increment_counter("sales_create_success_total", branch_id=branch_id, role=actor.role)
    observe_histogram_ms("sales_create_latency_ms", duration_ms, branch_id=branch_id, role=actor.role)
    log_event(
        "sales.create.success",
        request_id=request_id,
        correlation_id=request_id,
        branch_id=branch_id,
        actor_user_id=actor.id,
        sale_id=saved_sale.id,
        duration_ms=f"{duration_ms:.2f}",
    )
    return _receipt_from_sale(saved_sale)


async def void_sale(
    session: AsyncSession,
    *,
    branch_id: int,
    sale_id: int,
    actor: User,
    reason: str,
    request_id: str | None,
    redis_client: Redis | None = None,
) -> SaleVoidResult:
    started = perf_counter()
    increment_counter("sales_void_requests_total", branch_id=branch_id, role=actor.role)

    sale_stmt = (
        select(Sale)
        .where(Sale.id == sale_id, Sale.branch_id == branch_id)
        .options(selectinload(Sale.line_items))
    )
    sale = (await session.execute(sale_stmt)).scalar_one_or_none()
    if sale is None:
        raise SaleNotFoundError("Sale not found")
    if sale.status == "voided":
        raise SaleValidationError("Sale already voided")

    before_json = _serialize_sale(sale)

    movement_stmt = select(StockMovement).where(
        StockMovement.branch_id == branch_id,
        StockMovement.reference_id == f"sale:{sale_id}",
        StockMovement.movement_type == "sale",
    )
    original_movements = (await session.execute(movement_stmt)).scalars().all()
    if not original_movements:
        raise SaleValidationError("Sale stock movements not found")

    for movement in original_movements:
        session.add(
            StockMovement(
                product_id=movement.product_id,
                branch_id=branch_id,
                qty=-movement.qty,
                movement_type="adjustment",
                reference_id=f"sale_void:{sale_id}",
                created_by=actor.id,
            )
        )

    sale.status = "voided"
    sale.voided_at = datetime.now(timezone.utc)
    sale.voided_by_user_id = actor.id
    sale.void_reason = reason
    await session.commit()

    refreshed_sale = (await session.execute(sale_stmt)).scalar_one()

    await _publish_sale_write(
        session=session,
        redis_client=redis_client,
        branch_id=branch_id,
        sale=refreshed_sale,
        action="sale.void",
        before_json=before_json,
        after_json=_serialize_sale(refreshed_sale),
        actor_user_id=actor.id,
        request_id=request_id,
    )

    duration_ms = measure_elapsed_ms(started)
    increment_counter("sales_void_success_total", branch_id=branch_id, role=actor.role)
    observe_histogram_ms("sales_void_latency_ms", duration_ms, branch_id=branch_id, role=actor.role)
    log_event(
        "sales.void.success",
        request_id=request_id,
        correlation_id=request_id,
        branch_id=branch_id,
        actor_user_id=actor.id,
        sale_id=sale_id,
        duration_ms=f"{duration_ms:.2f}",
    )
    return _void_result_from_sale(refreshed_sale)


async def get_sale_receipt(
    session: AsyncSession,
    *,
    branch_id: int,
    sale_id: int,
) -> SaleReceipt:
    stmt = (
        select(Sale)
        .where(Sale.id == sale_id, Sale.branch_id == branch_id)
        .options(selectinload(Sale.line_items))
    )
    sale = (await session.execute(stmt)).scalar_one_or_none()
    if sale is None:
        raise SaleNotFoundError("Sale not found")
    return _receipt_from_sale(sale)


async def refund_sale(
    session: AsyncSession,
    *,
    branch_id: int,
    sale_id: int,
    actor: User,
    reason: str,
    request_id: str | None,
    redis_client: Redis | None = None,
) -> SaleRefundResult:
    started = perf_counter()
    increment_counter("sales_refund_requests_total", branch_id=branch_id, role=actor.role)

    sale_stmt = (
        select(Sale)
        .where(Sale.id == sale_id, Sale.branch_id == branch_id)
        .options(selectinload(Sale.line_items))
    )
    sale = (await session.execute(sale_stmt)).scalar_one_or_none()
    if sale is None:
        raise SaleNotFoundError("Sale not found")
    if sale.status == "refunded":
        raise SaleValidationError("Sale already refunded")
    if sale.status != "completed":
        raise SaleValidationError("Sale cannot be refunded from current status")

    before_json = _serialize_sale(sale)

    movement_stmt = select(StockMovement).where(
        StockMovement.branch_id == branch_id,
        StockMovement.reference_id == f"sale:{sale_id}",
        StockMovement.movement_type == "sale",
    )
    original_movements = (await session.execute(movement_stmt)).scalars().all()
    if not original_movements:
        raise SaleValidationError("Sale stock movements not found")

    for movement in original_movements:
        session.add(
            StockMovement(
                product_id=movement.product_id,
                branch_id=branch_id,
                qty=-movement.qty,
                movement_type="adjustment",
                reference_id=f"sale_refund:{sale_id}",
                created_by=actor.id,
            )
        )

    sale.status = "refunded"
    sale.refunded_at = datetime.now(timezone.utc)
    sale.refunded_by_user_id = actor.id
    sale.refund_reason = reason
    await session.commit()

    refreshed_sale = (await session.execute(sale_stmt)).scalar_one()

    await _publish_sale_write(
        session=session,
        redis_client=redis_client,
        branch_id=branch_id,
        sale=refreshed_sale,
        action="sale.refund",
        before_json=before_json,
        after_json=_serialize_sale(refreshed_sale),
        actor_user_id=actor.id,
        request_id=request_id,
    )

    duration_ms = measure_elapsed_ms(started)
    increment_counter("sales_refund_success_total", branch_id=branch_id, role=actor.role)
    observe_histogram_ms("sales_refund_latency_ms", duration_ms, branch_id=branch_id, role=actor.role)
    log_event(
        "sales.refund.success",
        request_id=request_id,
        correlation_id=request_id,
        branch_id=branch_id,
        actor_user_id=actor.id,
        sale_id=sale_id,
        duration_ms=f"{duration_ms:.2f}",
    )
    return _refund_result_from_sale(refreshed_sale)


async def get_daily_sales_summary(
    session: AsyncSession,
    *,
    branch_id: int,
    business_date: date,
) -> DailySalesSummary:
    day_start = datetime.combine(business_date, time.min, tzinfo=timezone.utc)
    day_end = datetime.combine(business_date, time.max, tzinfo=timezone.utc)

    base_filters = and_(Sale.branch_id == branch_id, Sale.created_at >= day_start, Sale.created_at <= day_end)

    totals_stmt = select(func.count(Sale.id), func.coalesce(func.sum(Sale.total), Decimal("0"))).where(base_filters)
    totals_row = (await session.execute(totals_stmt)).one()

    by_method_stmt = (
        select(Sale.payment_method, func.coalesce(func.sum(Sale.total), Decimal("0")).label("gross_total"))
        .where(base_filters)
        .group_by(Sale.payment_method)
        .order_by(Sale.payment_method)
    )
    by_method_rows = (await session.execute(by_method_stmt)).all()

    payment_method_totals = {row.payment_method: row.gross_total for row in by_method_rows}

    return DailySalesSummary(
        business_date=business_date,
        branch_id=branch_id,
        sales_count=int(totals_row[0] or 0),
        gross_total=totals_row[1] or Decimal("0"),
        payment_method_totals=payment_method_totals,
    )


async def create_sale_payment_intent(
    session: AsyncSession,
    *,
    branch_id: int,
    sale_id: int,
    payload: SalePaymentIntentRequest,
    request_id: str | None,
) -> SalePaymentIntentResult:
    stmt = select(Sale).where(Sale.id == sale_id, Sale.branch_id == branch_id)
    sale = (await session.execute(stmt)).scalar_one_or_none()
    if sale is None:
        raise SaleNotFoundError("Sale not found")

    payment_tenders = sale.payment_tenders or [{"payment_method": sale.payment_method, "amount": str(sale.total)}]
    provider = _payment_provider_for(payload.provider)

    authorizations: list[SalePaymentTenderAuthorization] = []
    for tender_index, tender in enumerate(payment_tenders):
        method = PaymentMethod(tender["payment_method"])
        if method == PaymentMethod.cash:
            continue
        amount = _quantize_money(Decimal(tender["amount"]))
        provider_auth = await provider.authorize_tender(
            sale_id=sale.id,
            branch_id=branch_id,
            tender_index=tender_index,
            payment_method=method,
            amount=amount,
            request_id=request_id,
        )
        authorizations.append(
            SalePaymentTenderAuthorization(
                tender_index=tender_index,
                payment_method=method,
                amount=provider_auth.amount,
                provider=provider_auth.provider,
                provider_reference=provider_auth.provider_reference,
                status=provider_auth.status,
            )
        )

    if not authorizations:
        raise SaleValidationError("Sale has no provider-eligible tenders")

    return SalePaymentIntentResult(
        sale_id=sale.id,
        branch_id=branch_id,
        provider=payload.provider,
        authorized_tenders=authorizations,
    )


async def reconcile_sale_payment(
    session: AsyncSession,
    *,
    branch_id: int,
    sale_id: int,
    payload: SalePaymentReconcileRequest,
    request_id: str | None,
) -> SalePaymentReconcileResult:
    stmt = select(Sale).where(Sale.id == sale_id, Sale.branch_id == branch_id)
    sale = (await session.execute(stmt)).scalar_one_or_none()
    if sale is None:
        raise SaleNotFoundError("Sale not found")

    provider = _payment_provider_for(payload.provider)
    digital_total = _digital_tender_total_from_sale(sale)

    reconciliation = await provider.reconcile_reference(
        sale_id=sale.id,
        branch_id=branch_id,
        provider_reference=payload.provider_reference,
        amount=digital_total,
        request_id=request_id,
    )

    return SalePaymentReconcileResult(
        sale_id=sale.id,
        branch_id=branch_id,
        provider=reconciliation.provider,
        provider_reference=reconciliation.provider_reference,
        status=reconciliation.status,
        reconciled_amount=reconciliation.amount,
        reconciled_at=reconciliation.reconciled_at,
    )


async def enqueue_sale_payment_reconciliation(
    session: AsyncSession,
    *,
    branch_id: int,
    sale_id: int,
    payload: SalePaymentReconcileRequest,
    request_id: str | None,
    redis_client: Redis | None = None,
) -> SalePaymentReconcileJobEnqueueResult:
    stmt = select(Sale).where(Sale.id == sale_id, Sale.branch_id == branch_id)
    sale = (await session.execute(stmt)).scalar_one_or_none()
    if sale is None:
        raise SaleNotFoundError("Sale not found")

    digital_total = _digital_tender_total_from_sale(sale)
    queued_at = datetime.now(timezone.utc)

    task_result = reconcile_sale_payment_task.delay(
        sale_id=sale.id,
        branch_id=branch_id,
        provider=payload.provider.value,
        provider_reference=payload.provider_reference,
        digital_total=str(digital_total),
        request_id=request_id,
    )
    job_id = task_result.id

    await _store_reconciliation_meta(
        redis_client,
        job_id,
        {
            "sale_id": sale.id,
            "branch_id": branch_id,
            "provider": payload.provider.value,
            "provider_reference": payload.provider_reference,
            "queued_at": queued_at.isoformat(),
        },
    )

    increment_counter("sales_payment_reconcile_async_enqueued_total", branch_id=branch_id, provider=payload.provider.value)
    log_event(
        "sales.payment_reconcile.async_enqueued",
        request_id=request_id,
        correlation_id=request_id,
        branch_id=branch_id,
        sale_id=sale.id,
        provider=payload.provider.value,
        job_id=job_id,
    )

    return SalePaymentReconcileJobEnqueueResult(
        job_id=job_id,
        sale_id=sale.id,
        branch_id=branch_id,
        provider=payload.provider,
        provider_reference=payload.provider_reference,
        status=ReconciliationJobStatus.queued,
        queued_at=queued_at,
    )


async def get_sale_payment_reconciliation_job_status(
    session: AsyncSession,
    *,
    branch_id: int,
    sale_id: int,
    job_id: str,
    redis_client: Redis | None = None,
) -> SalePaymentReconcileJobStatusResult:
    stmt = select(Sale.id).where(Sale.id == sale_id, Sale.branch_id == branch_id)
    sale_exists = (await session.execute(stmt)).scalar_one_or_none()
    if sale_exists is None:
        raise SaleNotFoundError("Sale not found")

    meta = await _load_reconciliation_meta(redis_client, job_id)
    if meta is None:
        raise ReconciliationJobNotFoundError("Reconciliation job not found")

    if int(meta["sale_id"]) != sale_id or int(meta["branch_id"]) != branch_id:
        raise ReconciliationJobNotFoundError("Reconciliation job not found")

    provider = PaymentProvider(meta["provider"])
    result = AsyncResult(job_id, app=celery_app)
    state = result.state

    status = ReconciliationJobStatus.queued
    started_at: datetime | None = None
    completed_at: datetime | None = None
    payload: SalePaymentReconcileResult | None = None
    error: str | None = None

    if state in {"STARTED", "RETRY"}:
        status = ReconciliationJobStatus.running
    elif state == "SUCCESS":
        status = ReconciliationJobStatus.succeeded
        completed_at = datetime.now(timezone.utc)
        task_payload = result.result or {}
        payload = SalePaymentReconcileResult(
            sale_id=int(task_payload["sale_id"]),
            branch_id=int(task_payload["branch_id"]),
            provider=PaymentProvider(task_payload["provider"]),
            provider_reference=str(task_payload["provider_reference"]),
            status=PaymentStatus(task_payload["status"]),
            reconciled_amount=Decimal(str(task_payload["reconciled_amount"])),
            reconciled_at=datetime.fromisoformat(str(task_payload["reconciled_at"])),
        )
    elif state == "FAILURE":
        status = ReconciliationJobStatus.failed
        completed_at = datetime.now(timezone.utc)
        error = str(result.result)

    queued_at = datetime.fromisoformat(str(meta["queued_at"]))

    return SalePaymentReconcileJobStatusResult(
        job_id=job_id,
        sale_id=sale_id,
        branch_id=branch_id,
        provider=provider,
        provider_reference=str(meta["provider_reference"]),
        status=status,
        queued_at=queued_at,
        started_at=started_at,
        completed_at=completed_at,
        result=payload,
        error=error,
    )

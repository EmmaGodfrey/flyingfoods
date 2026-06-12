"""Inventory service functions for product CRUD and computed stock queries."""

from collections.abc import Iterable
from datetime import datetime, timezone
from decimal import Decimal
import json
from typing import Any

from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import DomainEvent, get_event_bus
from app.core.observability import increment_counter, log_event
from app.db.models.category import Category
from app.db.models.product import Product
from app.db.models.stock_movement import StockMovement
from app.db.models.unit import Unit
from app.db.models.user import User
from app.schemas.inventory import LowStockAlert, ProductCreate, ProductUpdate, StockMovementCreate, StockSummary
from app.services.audit_service import INVENTORY_WRITE_EVENT
from app.services.search_indexing import delete_product_document, index_product_document


def stock_cache_key(branch_id: int) -> str:
    return f"inventory:stock:branch:{branch_id}"


def _serialize_decimal(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    return value


def _serialize_model_fields(model: Any, fields: Iterable[str]) -> dict[str, Any]:
    snapshot: dict[str, Any] = {}
    for field in fields:
        snapshot[field] = _serialize_decimal(getattr(model, field))
    return snapshot


def _serialize_product(product: Product) -> dict[str, Any]:
    return _serialize_model_fields(
        product,
        (
            "id",
            "branch_id",
            "name",
            "unit_id",
            "category_id",
            "supplier_id",
            "sku",
            "barcode",
            "reorder_level",
            "cost_price",
            "selling_price",
            "is_active",
        ),
    )


def _serialize_stock_movement(movement: StockMovement) -> dict[str, Any]:
    return _serialize_model_fields(
        movement,
        ("id", "product_id", "branch_id", "qty", "movement_type", "reference_id", "created_by"),
    )


async def _publish_inventory_write(
    *,
    session: AsyncSession,
    redis_client: Redis | None,
    branch_id: int,
    action: str,
    entity_type: str,
    entity_id: str,
    actor_user_id: int | None,
    request_id: str | None,
    before_json: dict[str, Any] | None,
    after_json: dict[str, Any] | None,
    source: str = "api",
) -> None:
    increment_counter(
        "inventory_write_publish_total",
        action=action,
        entity_type=entity_type,
        branch_id=branch_id,
    )
    log_event(
        "inventory.write.publish",
        request_id=request_id,
        correlation_id=request_id,
        branch_id=branch_id,
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
    )

    event = DomainEvent(
        type=INVENTORY_WRITE_EVENT,
        branch_id=branch_id,
        correlation_id=request_id,
        occurred_at=datetime.now(timezone.utc),
        payload={
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "actor_user_id": actor_user_id,
            "before_json": before_json,
            "after_json": after_json,
            "source": source,
        },
    )
    await get_event_bus().publish(event, context={"session": session, "redis_client": redis_client})


def evaluate_low_stock_rows(rows: Iterable[tuple[int, str, Decimal, Decimal]]) -> list[LowStockAlert]:
    alerts: list[LowStockAlert] = []
    for product_id, product_name, reorder_level, computed_stock in rows:
        if computed_stock < reorder_level:
            alerts.append(
                LowStockAlert(
                    product_id=product_id,
                    product_name=product_name,
                    reorder_level=reorder_level,
                    computed_stock=computed_stock,
                )
            )
    return alerts


async def list_products(
    session: AsyncSession,
    *,
    branch_id: int,
    limit: int,
    offset: int,
    search: str | None,
    category_id: int | None,
) -> tuple[list[Product], int]:
    filters = [Product.branch_id == branch_id]
    if search:
        filters.append(Product.name.ilike(f"%{search}%"))
    if category_id is not None:
        filters.append(Product.category_id == category_id)

    count_stmt = select(func.count()).select_from(Product).where(*filters)
    total = (await session.execute(count_stmt)).scalar_one()

    stmt = (
        select(Product)
        .where(*filters)
        .order_by(Product.id.desc())
        .limit(limit)
        .offset(offset)
    )
    items = (await session.execute(stmt)).scalars().all()
    return list(items), int(total)


async def list_categories(
    session: AsyncSession,
    *,
    branch_id: int,
    active_only: bool = True,
) -> list[Category]:
    filters = [Category.branch_id == branch_id]
    if active_only:
        filters.append(Category.is_active.is_(True))
    stmt = select(Category).where(*filters).order_by(Category.name.asc())
    return list((await session.execute(stmt)).scalars().all())


async def list_units(
    session: AsyncSession,
    *,
    branch_id: int,
    active_only: bool = True,
) -> list[Unit]:
    filters = [Unit.branch_id == branch_id]
    if active_only:
        filters.append(Unit.is_active.is_(True))
    stmt = select(Unit).where(*filters).order_by(Unit.name.asc())
    return list((await session.execute(stmt)).scalars().all())


async def create_product(
    session: AsyncSession,
    *,
    branch_id: int,
    payload: ProductCreate,
    actor_user_id: int | None,
    request_id: str | None,
    redis_client: Redis | None = None,
) -> Product:
    product = Product(branch_id=branch_id, **payload.model_dump())
    session.add(product)
    await session.commit()
    await session.refresh(product)
    await _publish_inventory_write(
        session=session,
        redis_client=redis_client,
        branch_id=branch_id,
        action="product.create",
        entity_type="product",
        entity_id=str(product.id),
        actor_user_id=actor_user_id,
        request_id=request_id,
        before_json=None,
        after_json=_serialize_product(product),
    )
    index_product_document(
        product_id=product.id,
        branch_id=product.branch_id,
        name=product.name,
        category_id=product.category_id,
        sku=product.sku,
        barcode=product.barcode,
        supplier_id=product.supplier_id,
        is_active=product.is_active,
    )
    return product


async def get_product_or_none(session: AsyncSession, *, branch_id: int, product_id: int) -> Product | None:
    stmt = select(Product).where(Product.id == product_id, Product.branch_id == branch_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def update_product(
    session: AsyncSession,
    *,
    branch_id: int,
    product: Product,
    payload: ProductUpdate,
    actor_user_id: int | None,
    request_id: str | None,
    redis_client: Redis | None = None,
) -> Product:
    before_json = _serialize_product(product)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, key, value)
    await session.commit()
    await session.refresh(product)
    await _publish_inventory_write(
        session=session,
        redis_client=redis_client,
        branch_id=branch_id,
        action="product.update",
        entity_type="product",
        entity_id=str(product.id),
        actor_user_id=actor_user_id,
        request_id=request_id,
        before_json=before_json,
        after_json=_serialize_product(product),
    )
    index_product_document(
        product_id=product.id,
        branch_id=product.branch_id,
        name=product.name,
        category_id=product.category_id,
        sku=product.sku,
        barcode=product.barcode,
        supplier_id=product.supplier_id,
        is_active=product.is_active,
    )
    return product


async def delete_product(
    session: AsyncSession,
    *,
    branch_id: int,
    product: Product,
    actor_user_id: int | None,
    request_id: str | None,
    redis_client: Redis | None = None,
) -> None:
    before_json = _serialize_product(product)
    entity_id = str(product.id)
    await session.delete(product)
    await session.commit()
    await _publish_inventory_write(
        session=session,
        redis_client=redis_client,
        branch_id=branch_id,
        action="product.delete",
        entity_type="product",
        entity_id=entity_id,
        actor_user_id=actor_user_id,
        request_id=request_id,
        before_json=before_json,
        after_json=None,
    )
    delete_product_document(product_id=int(entity_id), branch_id=branch_id)


async def create_stock_movement(
    session: AsyncSession,
    *,
    branch_id: int,
    actor: User,
    payload: StockMovementCreate,
    request_id: str | None,
    redis_client: Redis | None = None,
) -> StockMovement:
    movement = StockMovement(
        product_id=payload.product_id,
        branch_id=branch_id,
        qty=payload.qty,
        movement_type=payload.movement_type.value,
        reference_id=payload.reference_id,
        created_by=actor.id,
    )
    session.add(movement)
    await session.commit()
    await session.refresh(movement)
    await _publish_inventory_write(
        session=session,
        redis_client=redis_client,
        branch_id=branch_id,
        action=f"stock_movement.{movement.movement_type}",
        entity_type="stock_movement",
        entity_id=str(movement.id),
        actor_user_id=actor.id,
        request_id=request_id,
        before_json=None,
        after_json=_serialize_stock_movement(movement),
    )
    return movement


async def invalidate_stock_cache(redis_client: Redis | None, *, branch_id: int) -> None:
    if redis_client is None:
        return
    await redis_client.delete(stock_cache_key(branch_id))


async def get_computed_stock(
    session: AsyncSession,
    *,
    branch_id: int,
    product_id: int | None,
    redis_client: Redis | None = None,
) -> list[StockSummary]:
    if product_id is None and redis_client is not None:
        cached = await redis_client.get(stock_cache_key(branch_id))
        if cached:
            decoded = json.loads(cached)
            return [StockSummary(product_id=row["product_id"], computed_stock=Decimal(row["computed_stock"])) for row in decoded]

    stmt = (
        select(StockMovement.product_id, func.coalesce(func.sum(StockMovement.qty), 0).label("computed_stock"))
        .where(StockMovement.branch_id == branch_id)
        .group_by(StockMovement.product_id)
        .order_by(StockMovement.product_id)
    )
    if product_id is not None:
        stmt = stmt.where(StockMovement.product_id == product_id)

    rows = (await session.execute(stmt)).all()
    summaries = [StockSummary(product_id=row.product_id, computed_stock=row.computed_stock) for row in rows]

    if product_id is None and redis_client is not None:
        payload = [{"product_id": row.product_id, "computed_stock": str(row.computed_stock)} for row in summaries]
        await redis_client.setex(stock_cache_key(branch_id), 60, json.dumps(payload))

    return summaries


async def get_low_stock_alerts(session: AsyncSession, *, branch_id: int) -> list[LowStockAlert]:
    stock_subquery = (
        select(
            StockMovement.product_id.label("product_id"),
            func.coalesce(func.sum(StockMovement.qty), 0).label("computed_stock"),
        )
        .where(StockMovement.branch_id == branch_id)
        .group_by(StockMovement.product_id)
        .subquery()
    )

    stmt = (
        select(
            Product.id,
            Product.name,
            Product.reorder_level,
            func.coalesce(stock_subquery.c.computed_stock, 0),
        )
        .outerjoin(stock_subquery, stock_subquery.c.product_id == Product.id)
        .where(Product.branch_id == branch_id, Product.is_active.is_(True))
        .order_by(Product.id)
    )

    rows = (await session.execute(stmt)).all()
    return evaluate_low_stock_rows(rows)


async def list_stock_movements(
    session: AsyncSession,
    *,
    branch_id: int,
    limit: int,
    offset: int,
    product_id: int | None,
    movement_type: str | None,
    occurred_after: datetime | None,
    occurred_before: datetime | None,
) -> tuple[list[StockMovement], int]:
    filters = [StockMovement.branch_id == branch_id]
    if product_id is not None:
        filters.append(StockMovement.product_id == product_id)
    if movement_type:
        filters.append(StockMovement.movement_type == movement_type)
    if occurred_after is not None:
        filters.append(StockMovement.created_at >= occurred_after)
    if occurred_before is not None:
        filters.append(StockMovement.created_at <= occurred_before)

    count_stmt = select(func.count()).select_from(StockMovement).where(*filters)
    total = (await session.execute(count_stmt)).scalar_one()

    stmt = (
        select(StockMovement)
        .where(*filters)
        .order_by(StockMovement.created_at.desc(), StockMovement.id.desc())
        .limit(limit)
        .offset(offset)
    )
    items = (await session.execute(stmt)).scalars().all()
    return list(items), int(total)

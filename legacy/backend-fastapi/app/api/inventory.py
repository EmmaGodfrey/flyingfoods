"""Inventory endpoints: product CRUD, stock movements, computed stock, and low stock alerts."""
from datetime import datetime

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi import Request
from redis.asyncio import Redis
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_branch, get_current_user, require_role
from app.core.redis import get_redis
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.inventory import (
    CategoryRead,
    LowStockAlert,
    ProductCreate,
    ProductListResponse,
    ProductRead,
    ProductUpdate,
    StockMovementCreate,
    StockMovementListResponse,
    StockMovementRead,
    StockSummary,
    UnitRead,
)
from app.services.inventory_service import (
    create_product,
    create_stock_movement,
    delete_product,
    get_computed_stock,
    get_low_stock_alerts,
    get_product_or_none,
    list_stock_movements,
    list_categories,
    list_products,
    list_units,
    update_product,
)

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/categories", response_model=list[CategoryRead])
async def get_categories_endpoint(
    active_only: bool = Query(default=True),
    branch_id: int = Depends(get_current_branch),
    session: AsyncSession = Depends(get_db),
) -> list[CategoryRead]:
    return await list_categories(session, branch_id=branch_id, active_only=active_only)


@router.get("/units", response_model=list[UnitRead])
async def get_units_endpoint(
    active_only: bool = Query(default=True),
    branch_id: int = Depends(get_current_branch),
    session: AsyncSession = Depends(get_db),
) -> list[UnitRead]:
    return await list_units(session, branch_id=branch_id, active_only=active_only)


def _request_id_from(request: Request | None) -> str:
    if request is None:
        return str(uuid4())
    return request.headers.get("x-request-id", str(uuid4()))


@router.get("/products", response_model=ProductListResponse)
async def get_products(
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None),
    category_id: int | None = Query(default=None, ge=1),
    branch_id: int = Depends(get_current_branch),
    session: AsyncSession = Depends(get_db),
) -> ProductListResponse:
    items, total = await list_products(
        session,
        branch_id=branch_id,
        limit=limit,
        offset=offset,
        search=search,
        category_id=category_id,
    )
    return ProductListResponse(items=items, total=total, limit=limit, offset=offset)


@router.post(
    "/products",
    response_model=ProductRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("superadmin", "admin", "manager", "inventory_officer"))],
)
async def create_product_endpoint(
    payload: ProductCreate,
    request: Request,
    branch_id: int = Depends(get_current_branch),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ProductRead:
    try:
        product = await create_product(
            session,
            branch_id=branch_id,
            payload=payload,
            actor_user_id=current_user.id,
            request_id=_request_id_from(request),
            redis_client=None,
        )
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid product references or duplicate data") from exc
    return product


@router.get("/products/{product_id}", response_model=ProductRead)
async def get_product_endpoint(
    product_id: int,
    branch_id: int = Depends(get_current_branch),
    session: AsyncSession = Depends(get_db),
) -> ProductRead:
    product = await get_product_or_none(session, branch_id=branch_id, product_id=product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


@router.put(
    "/products/{product_id}",
    response_model=ProductRead,
    dependencies=[Depends(require_role("superadmin", "admin", "manager", "inventory_officer"))],
)
async def update_product_endpoint(
    product_id: int,
    payload: ProductUpdate,
    request: Request,
    branch_id: int = Depends(get_current_branch),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ProductRead:
    product = await get_product_or_none(session, branch_id=branch_id, product_id=product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    try:
        product = await update_product(
            session,
            branch_id=branch_id,
            product=product,
            payload=payload,
            actor_user_id=current_user.id,
            request_id=_request_id_from(request),
            redis_client=None,
        )
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid product update") from exc
    return product


@router.delete(
    "/products/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role("superadmin", "admin", "manager"))],
)
async def delete_product_endpoint(
    product_id: int,
    request: Request,
    branch_id: int = Depends(get_current_branch),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    product = await get_product_or_none(session, branch_id=branch_id, product_id=product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    try:
        await delete_product(
            session,
            branch_id=branch_id,
            product=product,
            actor_user_id=current_user.id,
            request_id=_request_id_from(request),
            redis_client=None,
        )
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Product is referenced by other records") from exc


@router.post(
    "/movements",
    response_model=StockMovementRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("superadmin", "admin", "manager", "inventory_officer", "cashier"))],
)
async def create_stock_movement_endpoint(
    payload: StockMovementCreate,
    request: Request,
    branch_id: int = Depends(get_current_branch),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> StockMovementRead:
    product = await get_product_or_none(session, branch_id=branch_id, product_id=payload.product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found in current branch")

    movement = await create_stock_movement(
        session,
        branch_id=branch_id,
        actor=current_user,
        payload=payload,
        request_id=_request_id_from(request),
        redis_client=None,
    )
    return movement


@router.get("/movements", response_model=StockMovementListResponse)
async def get_stock_movement_history_endpoint(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    product_id: int | None = Query(default=None, ge=1),
    movement_type: str | None = Query(default=None),
    occurred_after: str | None = Query(default=None),
    occurred_before: str | None = Query(default=None),
    branch_id: int = Depends(get_current_branch),
    session: AsyncSession = Depends(get_db),
) -> StockMovementListResponse:
    parsed_after = None
    parsed_before = None
    if occurred_after:
        try:
            from datetime import datetime

            parsed_after = datetime.fromisoformat(occurred_after)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid occurred_after format") from exc
    if occurred_before:
        try:
            from datetime import datetime

            parsed_before = datetime.fromisoformat(occurred_before)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid occurred_before format") from exc

    if movement_type is not None and movement_type not in {"receive", "sale", "waste", "adjustment"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid movement_type")

    items, total = await list_stock_movements(
        session,
        branch_id=branch_id,
        limit=limit,
        offset=offset,
        product_id=product_id,
        movement_type=movement_type,
        occurred_after=parsed_after,
        occurred_before=parsed_before,
    )
    return StockMovementListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/stock/current", response_model=list[StockSummary])
async def get_current_stock_endpoint(
    product_id: int | None = Query(default=None, ge=1),
    branch_id: int = Depends(get_current_branch),
    session: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
) -> list[StockSummary]:
    return await get_computed_stock(
        session,
        branch_id=branch_id,
        product_id=product_id,
        redis_client=redis_client,
    )


@router.get("/stock/low", response_model=list[LowStockAlert])
async def get_low_stock_endpoint(
    branch_id: int = Depends(get_current_branch),
    session: AsyncSession = Depends(get_db),
) -> list[LowStockAlert]:
    return await get_low_stock_alerts(session, branch_id=branch_id)

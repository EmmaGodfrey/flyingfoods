"""Procurement APIs for purchase orders, goods receipts, and reports."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_branch, get_current_user, require_role
from app.core.redis import get_redis
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.procurement import (
    GoodsReceivedNoteCreate,
    GoodsReceivedNoteRead,
    ProcurementOrdersReportResponse,
    PurchaseOrderCreate,
    PurchaseOrderListResponse,
    PurchaseOrderRead,
    SupplierCreate,
    SupplierListResponse,
    SupplierRead,
    SupplierUpdate,
)
from app.schemas.reports import ProcurementSpendResponse
from app.services.procurement_service import (
    ProcurementConflictError,
    ProcurementNotFoundError,
    ProcurementValidationError,
    approve_purchase_order,
    create_goods_received_note,
    create_purchase_order,
    get_procurement_orders_report,
    get_procurement_spend_report_week6,
    list_purchase_orders,
    submit_purchase_order,
)
from app.services.supplier_service import create_supplier, delete_supplier, get_supplier_or_none, list_suppliers, update_supplier

router = APIRouter(prefix="/procurement", tags=["procurement"])


def _request_id_from(request: Request) -> str:
    return request.headers.get("x-request-id", str(uuid4()))


def _parse_datetime(value: str | None, *, field_name: str) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid {field_name} format") from exc


def _translate_procurement_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ProcurementNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, ProcurementConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, ProcurementValidationError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected procurement error")


@router.post(
    "/orders",
    response_model=PurchaseOrderRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("superadmin", "admin", "manager"))],
)
async def create_purchase_order_endpoint(
    payload: PurchaseOrderCreate,
    request: Request,
    branch_id: int = Depends(get_current_branch),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PurchaseOrderRead:
    try:
        return await create_purchase_order(
            session,
            branch_id=branch_id,
            actor=current_user,
            payload=payload,
            request_id=_request_id_from(request),
        )
    except Exception as exc:  # noqa: BLE001
        raise _translate_procurement_error(exc) from exc


@router.get(
    "/orders",
    response_model=PurchaseOrderListResponse,
    dependencies=[Depends(require_role("superadmin", "admin", "manager", "inventory_officer"))],
)
async def list_purchase_orders_endpoint(
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default=None, alias="status"),
    supplier_id: int | None = Query(default=None, ge=1),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    branch_id: int = Depends(get_current_branch),
    session: AsyncSession = Depends(get_db),
) -> PurchaseOrderListResponse:
    parsed_from = _parse_datetime(date_from, field_name="date_from")
    parsed_to = _parse_datetime(date_to, field_name="date_to")
    return await list_purchase_orders(
        session,
        branch_id=branch_id,
        limit=limit,
        offset=offset,
        status_filter=status_filter,
        supplier_id=supplier_id,
        date_from=parsed_from,
        date_to=parsed_to,
    )


@router.put(
    "/orders/{purchase_order_id}/submit",
    response_model=PurchaseOrderRead,
    dependencies=[Depends(require_role("superadmin", "admin", "manager"))],
)
async def submit_purchase_order_endpoint(
    purchase_order_id: int,
    request: Request,
    branch_id: int = Depends(get_current_branch),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PurchaseOrderRead:
    try:
        return await submit_purchase_order(
            session,
            branch_id=branch_id,
            purchase_order_id=purchase_order_id,
            actor=current_user,
            request_id=_request_id_from(request),
        )
    except Exception as exc:  # noqa: BLE001
        raise _translate_procurement_error(exc) from exc


@router.put(
    "/orders/{purchase_order_id}/approve",
    response_model=PurchaseOrderRead,
    dependencies=[Depends(require_role("superadmin", "admin"))],
)
async def approve_purchase_order_endpoint(
    purchase_order_id: int,
    request: Request,
    branch_id: int = Depends(get_current_branch),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PurchaseOrderRead:
    try:
        return await approve_purchase_order(
            session,
            branch_id=branch_id,
            purchase_order_id=purchase_order_id,
            actor=current_user,
            request_id=_request_id_from(request),
        )
    except Exception as exc:  # noqa: BLE001
        raise _translate_procurement_error(exc) from exc


@router.post(
    "/grn",
    response_model=GoodsReceivedNoteRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("superadmin", "admin", "manager", "inventory_officer"))],
)
async def create_goods_received_note_endpoint(
    payload: GoodsReceivedNoteCreate,
    request: Request,
    branch_id: int = Depends(get_current_branch),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
) -> GoodsReceivedNoteRead:
    try:
        return await create_goods_received_note(
            session,
            branch_id=branch_id,
            actor=current_user,
            payload=payload,
            request_id=_request_id_from(request),
            redis_client=redis_client,
        )
    except Exception as exc:  # noqa: BLE001
        raise _translate_procurement_error(exc) from exc


@router.get(
    "/reports/orders",
    response_model=ProcurementOrdersReportResponse,
    dependencies=[Depends(require_role("superadmin", "admin", "manager"))],
)
async def get_procurement_orders_report_endpoint(
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default=None, alias="status"),
    supplier_id: int | None = Query(default=None, ge=1),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    branch_id: int = Depends(get_current_branch),
    session: AsyncSession = Depends(get_db),
) -> ProcurementOrdersReportResponse:
    parsed_from = _parse_datetime(date_from, field_name="date_from")
    parsed_to = _parse_datetime(date_to, field_name="date_to")
    return await get_procurement_orders_report(
        session,
        branch_id=branch_id,
        limit=limit,
        offset=offset,
        status_filter=status_filter,
        supplier_id=supplier_id,
        date_from=parsed_from,
        date_to=parsed_to,
    )


@router.get(
    "/reports/spend",
    response_model=ProcurementSpendResponse,
    dependencies=[Depends(require_role("superadmin", "admin", "manager"))],
)
async def get_procurement_spend_report_week6_endpoint(
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    branch_id: int = Depends(get_current_branch),
    session: AsyncSession = Depends(get_db),
) -> ProcurementSpendResponse:
    parsed_from = _parse_datetime(date_from, field_name="date_from")
    parsed_to = _parse_datetime(date_to, field_name="date_to")
    return await get_procurement_spend_report_week6(
        session,
        branch_id=branch_id,
        date_from=parsed_from,
        date_to=parsed_to,
    )


@router.post(
    "/suppliers",
    response_model=SupplierRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("superadmin", "admin", "manager"))],
)
async def create_supplier_endpoint(
    payload: SupplierCreate,
    branch_id: int = Depends(get_current_branch),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SupplierRead:
    return await create_supplier(session, branch_id=branch_id, actor=current_user, payload=payload)


@router.get(
    "/suppliers",
    response_model=SupplierListResponse,
    dependencies=[Depends(require_role("superadmin", "admin", "manager", "inventory_officer"))],
)
async def list_suppliers_endpoint(
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    branch_id: int = Depends(get_current_branch),
    session: AsyncSession = Depends(get_db),
) -> SupplierListResponse:
    return await list_suppliers(
        session,
        branch_id=branch_id,
        limit=limit,
        offset=offset,
        search=search,
        is_active=is_active,
    )


@router.put(
    "/suppliers/{supplier_id}",
    response_model=SupplierRead,
    dependencies=[Depends(require_role("superadmin", "admin", "manager"))],
)
async def update_supplier_endpoint(
    supplier_id: int,
    payload: SupplierUpdate,
    branch_id: int = Depends(get_current_branch),
    session: AsyncSession = Depends(get_db),
) -> SupplierRead:
    supplier = await get_supplier_or_none(session, branch_id=branch_id, supplier_id=supplier_id)
    if supplier is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    return await update_supplier(session, branch_id=branch_id, supplier=supplier, payload=payload)


@router.delete(
    "/suppliers/{supplier_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role("superadmin", "admin", "manager"))],
)
async def delete_supplier_endpoint(
    supplier_id: int,
    branch_id: int = Depends(get_current_branch),
    session: AsyncSession = Depends(get_db),
) -> None:
    supplier = await get_supplier_or_none(session, branch_id=branch_id, supplier_id=supplier_id)
    if supplier is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    await delete_supplier(session, branch_id=branch_id, supplier=supplier)

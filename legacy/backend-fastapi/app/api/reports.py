"""Reporting APIs for sales, inventory, and procurement analytics."""

from __future__ import annotations

import csv
from datetime import datetime
from io import StringIO
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_branch, get_current_user, require_role
from app.core.redis import get_redis
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.reports import (
    InventoryMovementReportResponse,
    InventoryValuationResponse,
    ProcurementSpendResponse,
    ReportTaskEnqueueResponse,
    ReportTaskStatusResponse,
    SalesReportResponse,
)
from app.services.reporting_service import (
    ReportTaskNotFoundError,
    enqueue_procurement_spend_report_task,
    get_inventory_movements_report,
    get_inventory_valuation_report,
    get_procurement_spend_report,
    get_report_task_status,
    get_sales_report,
)

router = APIRouter(prefix="/reports", tags=["reports"])


def _request_id_from(request: Request) -> str:
    return request.headers.get("x-request-id", str(uuid4()))


def _parse_datetime(value: str | None, *, field_name: str) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid {field_name} format") from exc


@router.get(
    "/sales",
    response_model=SalesReportResponse,
    dependencies=[Depends(require_role("superadmin", "admin", "manager"))],
)
async def get_sales_report_endpoint(
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    cashier_user_id: int | None = Query(default=None, ge=1),
    product_id: int | None = Query(default=None, ge=1),
    payment_method: str | None = Query(default=None),
    branch_id: int = Depends(get_current_branch),
    session: AsyncSession = Depends(get_db),
) -> SalesReportResponse:
    parsed_from = _parse_datetime(date_from, field_name="date_from")
    parsed_to = _parse_datetime(date_to, field_name="date_to")

    return await get_sales_report(
        session,
        branch_id=branch_id,
        date_from=parsed_from,
        date_to=parsed_to,
        cashier_user_id=cashier_user_id,
        product_id=product_id,
        payment_method=payment_method,
    )


@router.get(
    "/sales/export/csv",
    dependencies=[Depends(require_role("superadmin", "admin", "manager"))],
)
async def get_sales_report_csv_endpoint(
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    cashier_user_id: int | None = Query(default=None, ge=1),
    product_id: int | None = Query(default=None, ge=1),
    payment_method: str | None = Query(default=None),
    branch_id: int = Depends(get_current_branch),
    session: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    parsed_from = _parse_datetime(date_from, field_name="date_from")
    parsed_to = _parse_datetime(date_to, field_name="date_to")

    report = await get_sales_report(
        session,
        branch_id=branch_id,
        date_from=parsed_from,
        date_to=parsed_to,
        cashier_user_id=cashier_user_id,
        product_id=product_id,
        payment_method=payment_method,
    )

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["sale_id", "sold_at", "cashier_user_id", "payment_method", "product_id", "product_name", "quantity", "unit_price", "line_total"])
    for line in report.lines:
        writer.writerow(
            [
                line.sale_id,
                line.sold_at.isoformat(),
                line.cashier_user_id,
                line.payment_method,
                line.product_id,
                line.product_name,
                str(line.quantity),
                str(line.unit_price),
                str(line.line_total),
            ]
        )

    csv_data = buffer.getvalue()
    headers = {"Content-Disposition": "attachment; filename=sales_report.csv"}
    return StreamingResponse(iter([csv_data]), media_type="text/csv", headers=headers)


@router.get(
    "/inventory/valuation",
    response_model=InventoryValuationResponse,
    dependencies=[Depends(require_role("superadmin", "admin", "manager"))],
)
async def get_inventory_valuation_report_endpoint(
    branch_id: int = Depends(get_current_branch),
    session: AsyncSession = Depends(get_db),
) -> InventoryValuationResponse:
    return await get_inventory_valuation_report(session, branch_id=branch_id)


@router.get(
    "/inventory/movements",
    response_model=InventoryMovementReportResponse,
    dependencies=[Depends(require_role("superadmin", "admin", "manager"))],
)
async def get_inventory_movements_report_endpoint(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    movement_type: str | None = Query(default=None),
    product_id: int | None = Query(default=None, ge=1),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    branch_id: int = Depends(get_current_branch),
    session: AsyncSession = Depends(get_db),
) -> InventoryMovementReportResponse:
    parsed_from = _parse_datetime(date_from, field_name="date_from")
    parsed_to = _parse_datetime(date_to, field_name="date_to")

    if movement_type is not None and movement_type not in {"receive", "sale", "waste", "adjustment"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid movement_type")

    return await get_inventory_movements_report(
        session,
        branch_id=branch_id,
        limit=limit,
        offset=offset,
        movement_type=movement_type,
        product_id=product_id,
        date_from=parsed_from,
        date_to=parsed_to,
    )


@router.get(
    "/procurement/spend",
    response_model=ProcurementSpendResponse,
    dependencies=[Depends(require_role("superadmin", "admin", "manager"))],
)
async def get_procurement_spend_report_endpoint(
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    branch_id: int = Depends(get_current_branch),
    session: AsyncSession = Depends(get_db),
) -> ProcurementSpendResponse:
    parsed_from = _parse_datetime(date_from, field_name="date_from")
    parsed_to = _parse_datetime(date_to, field_name="date_to")

    return await get_procurement_spend_report(
        session,
        branch_id=branch_id,
        date_from=parsed_from,
        date_to=parsed_to,
    )


@router.post(
    "/procurement/spend/async",
    response_model=ReportTaskEnqueueResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_role("superadmin", "admin", "manager"))],
)
async def enqueue_procurement_spend_report_endpoint(
    request: Request,
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    branch_id: int = Depends(get_current_branch),
    session: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
) -> ReportTaskEnqueueResponse:
    parsed_from = _parse_datetime(date_from, field_name="date_from")
    parsed_to = _parse_datetime(date_to, field_name="date_to")

    return await enqueue_procurement_spend_report_task(
        session,
        branch_id=branch_id,
        date_from=parsed_from,
        date_to=parsed_to,
        request_id=_request_id_from(request),
        redis_client=redis_client,
    )


@router.get(
    "/tasks/{task_id}/status",
    response_model=ReportTaskStatusResponse,
    dependencies=[Depends(require_role("superadmin", "admin", "manager"))],
)
async def get_report_task_status_endpoint(
    task_id: str,
    current_user: User = Depends(get_current_user),
    branch_id: int = Depends(get_current_branch),
    redis_client: Redis = Depends(get_redis),
) -> ReportTaskStatusResponse:
    try:
        return await get_report_task_status(
            branch_id=branch_id,
            task_id=task_id,
            redis_client=redis_client,
        )
    except ReportTaskNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

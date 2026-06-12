"""Sales APIs for POS checkout, receipt lookup, and daily summary."""

from __future__ import annotations

from datetime import date, datetime, timezone
from time import perf_counter
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_branch, get_current_user, require_role
from app.core.observability import increment_counter, log_event, measure_elapsed_ms, observe_histogram_ms
from app.core.redis import get_redis
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.sales import (
    DailySalesSummary,
    SaleCreate,
    SalePaymentIntentRequest,
    SalePaymentIntentResult,
    SalePaymentReconcileJobEnqueueResult,
    SalePaymentReconcileJobStatusResult,
    SalePaymentReconcileRequest,
    SalePaymentReconcileResult,
    SaleReceipt,
    SaleRefundRequest,
    SaleRefundResult,
    SaleVoidRequest,
    SaleVoidResult,
)
from app.services.sales_service import (
    PaymentProviderError,
    ReconciliationJobNotFoundError,
    SaleNotFoundError,
    SaleProductNotFoundError,
    SaleValidationError,
    create_sale_payment_intent,
    create_sale,
    enqueue_sale_payment_reconciliation,
    get_daily_sales_summary,
    get_sale_payment_reconciliation_job_status,
    get_sale_receipt,
    reconcile_sale_payment,
    refund_sale,
    void_sale,
)

router = APIRouter(prefix="/sales", tags=["sales"])


def _request_id_from(request: Request) -> str:
    return request.headers.get("x-request-id", str(uuid4()))


@router.post(
    "",
    response_model=SaleReceipt,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("superadmin", "admin", "manager", "cashier"))],
)
async def create_sale_endpoint(
    payload: SaleCreate,
    request: Request,
    branch_id: int = Depends(get_current_branch),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
) -> SaleReceipt:
    request_id = _request_id_from(request)

    try:
        return await create_sale(
            session,
            branch_id=branch_id,
            actor=current_user,
            payload=payload,
            request_id=request_id,
            redis_client=redis_client,
        )
    except SaleProductNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except SaleValidationError as exc:
        increment_counter("sales_create_failures_total", branch_id=branch_id, role=current_user.role)
        log_event(
            "sales.create.validation_error",
            request_id=request_id,
            correlation_id=request_id,
            branch_id=branch_id,
            actor_user_id=current_user.id,
            detail=str(exc),
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get(
    "/summary/daily",
    response_model=DailySalesSummary,
    dependencies=[Depends(require_role("superadmin", "admin", "manager", "cashier"))],
)
async def get_daily_summary_endpoint(
    request: Request,
    business_date: date | None = Query(default=None),
    branch_id: int = Depends(get_current_branch),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DailySalesSummary:
    request_id = _request_id_from(request)
    target_date = business_date or datetime.now(timezone.utc).date()

    started = perf_counter()
    increment_counter("sales_daily_summary_requests_total", branch_id=branch_id, role=current_user.role)
    summary = await get_daily_sales_summary(session, branch_id=branch_id, business_date=target_date)
    duration_ms = measure_elapsed_ms(started)

    observe_histogram_ms("sales_daily_summary_latency_ms", duration_ms, branch_id=branch_id, role=current_user.role)
    log_event(
        "sales.daily_summary.success",
        request_id=request_id,
        correlation_id=request_id,
        branch_id=branch_id,
        actor_user_id=current_user.id,
        business_date=target_date.isoformat(),
        sales_count=summary.sales_count,
        duration_ms=f"{duration_ms:.2f}",
    )
    return summary


@router.get(
    "/{sale_id}/receipt",
    response_model=SaleReceipt,
    dependencies=[Depends(require_role("superadmin", "admin", "manager", "cashier"))],
)
async def get_sale_receipt_endpoint(
    sale_id: int,
    request: Request,
    branch_id: int = Depends(get_current_branch),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SaleReceipt:
    request_id = _request_id_from(request)

    started = perf_counter()
    increment_counter("sales_receipt_requests_total", branch_id=branch_id, role=current_user.role)
    try:
        receipt = await get_sale_receipt(session, branch_id=branch_id, sale_id=sale_id)
    except SaleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    duration_ms = measure_elapsed_ms(started)
    observe_histogram_ms("sales_receipt_latency_ms", duration_ms, branch_id=branch_id, role=current_user.role)
    log_event(
        "sales.receipt.success",
        request_id=request_id,
        correlation_id=request_id,
        branch_id=branch_id,
        actor_user_id=current_user.id,
        sale_id=sale_id,
        duration_ms=f"{duration_ms:.2f}",
    )
    return receipt


@router.post(
    "/{sale_id}/void",
    response_model=SaleVoidResult,
    dependencies=[Depends(require_role("superadmin", "admin", "manager", "cashier"))],
)
async def void_sale_endpoint(
    sale_id: int,
    payload: SaleVoidRequest,
    request: Request,
    branch_id: int = Depends(get_current_branch),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
) -> SaleVoidResult:
    request_id = _request_id_from(request)

    try:
        return await void_sale(
            session,
            branch_id=branch_id,
            sale_id=sale_id,
            actor=current_user,
            reason=payload.reason,
            request_id=request_id,
            redis_client=redis_client,
        )
    except SaleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except SaleValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/{sale_id}/refund",
    response_model=SaleRefundResult,
    dependencies=[Depends(require_role("superadmin", "admin", "manager", "cashier"))],
)
async def refund_sale_endpoint(
    sale_id: int,
    payload: SaleRefundRequest,
    request: Request,
    branch_id: int = Depends(get_current_branch),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
) -> SaleRefundResult:
    request_id = _request_id_from(request)

    try:
        return await refund_sale(
            session,
            branch_id=branch_id,
            sale_id=sale_id,
            actor=current_user,
            reason=payload.reason,
            request_id=request_id,
            redis_client=redis_client,
        )
    except SaleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except SaleValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/{sale_id}/payments/intent",
    response_model=SalePaymentIntentResult,
    dependencies=[Depends(require_role("superadmin", "admin", "manager", "cashier"))],
)
async def create_sale_payment_intent_endpoint(
    sale_id: int,
    payload: SalePaymentIntentRequest,
    request: Request,
    branch_id: int = Depends(get_current_branch),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SalePaymentIntentResult:
    request_id = _request_id_from(request)

    try:
        return await create_sale_payment_intent(
            session,
            branch_id=branch_id,
            sale_id=sale_id,
            payload=payload,
            request_id=request_id,
        )
    except SaleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (SaleValidationError, PaymentProviderError) as exc:
        log_event(
            "sales.payment_intent.error",
            request_id=request_id,
            correlation_id=request_id,
            branch_id=branch_id,
            actor_user_id=current_user.id,
            sale_id=sale_id,
            detail=str(exc),
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/{sale_id}/payments/reconcile",
    response_model=SalePaymentReconcileResult,
    dependencies=[Depends(require_role("superadmin", "admin", "manager", "cashier"))],
)
async def reconcile_sale_payment_endpoint(
    sale_id: int,
    payload: SalePaymentReconcileRequest,
    request: Request,
    branch_id: int = Depends(get_current_branch),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SalePaymentReconcileResult:
    request_id = _request_id_from(request)

    try:
        return await reconcile_sale_payment(
            session,
            branch_id=branch_id,
            sale_id=sale_id,
            payload=payload,
            request_id=request_id,
        )
    except SaleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (SaleValidationError, PaymentProviderError) as exc:
        log_event(
            "sales.payment_reconcile.error",
            request_id=request_id,
            correlation_id=request_id,
            branch_id=branch_id,
            actor_user_id=current_user.id,
            sale_id=sale_id,
            detail=str(exc),
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/{sale_id}/payments/reconcile/async",
    response_model=SalePaymentReconcileJobEnqueueResult,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_role("superadmin", "admin", "manager", "cashier"))],
)
async def enqueue_sale_payment_reconcile_endpoint(
    sale_id: int,
    payload: SalePaymentReconcileRequest,
    request: Request,
    branch_id: int = Depends(get_current_branch),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
) -> SalePaymentReconcileJobEnqueueResult:
    request_id = _request_id_from(request)

    try:
        return await enqueue_sale_payment_reconciliation(
            session,
            branch_id=branch_id,
            sale_id=sale_id,
            payload=payload,
            request_id=request_id,
            redis_client=redis_client,
        )
    except SaleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (SaleValidationError, PaymentProviderError) as exc:
        log_event(
            "sales.payment_reconcile.async_error",
            request_id=request_id,
            correlation_id=request_id,
            branch_id=branch_id,
            actor_user_id=current_user.id,
            sale_id=sale_id,
            detail=str(exc),
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get(
    "/{sale_id}/payments/reconcile/jobs/{job_id}",
    response_model=SalePaymentReconcileJobStatusResult,
    dependencies=[Depends(require_role("superadmin", "admin", "manager", "cashier"))],
)
async def get_sale_payment_reconcile_job_status_endpoint(
    sale_id: int,
    job_id: str,
    request: Request,
    branch_id: int = Depends(get_current_branch),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
) -> SalePaymentReconcileJobStatusResult:
    request_id = _request_id_from(request)

    try:
        return await get_sale_payment_reconciliation_job_status(
            session,
            branch_id=branch_id,
            sale_id=sale_id,
            job_id=job_id,
            redis_client=redis_client,
        )
    except SaleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ReconciliationJobNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (SaleValidationError, PaymentProviderError) as exc:
        log_event(
            "sales.payment_reconcile.job_status.error",
            request_id=request_id,
            correlation_id=request_id,
            branch_id=branch_id,
            actor_user_id=current_user.id,
            sale_id=sale_id,
            detail=str(exc),
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

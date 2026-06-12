"""Celery tasks for sales payment reconciliation workflows."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from time import perf_counter

from app.core.celery_app import celery_app
from app.core.observability import increment_counter, log_event, measure_elapsed_ms, observe_histogram_ms

SIMULATED_PROVIDER = "simulated"
RECONCILE_SALE_PAYMENT_TASK = "app.tasks.sales_tasks.reconcile_sale_payment_task"


def _quantize_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"))


@celery_app.task(name=RECONCILE_SALE_PAYMENT_TASK)
def reconcile_sale_payment_task(
    *,
    sale_id: int,
    branch_id: int,
    provider: str,
    provider_reference: str,
    digital_total: str,
    request_id: str | None,
) -> dict[str, str]:
    started = perf_counter()
    increment_counter("sales_payment_reconcile_async_started_total", branch_id=branch_id, provider=provider)

    try:
        if provider != SIMULATED_PROVIDER:
            raise ValueError("Unsupported payment provider")

        reference_prefix = f"sim-{branch_id}-{sale_id}-"
        if not provider_reference.startswith(reference_prefix):
            raise ValueError("Provider reference does not match sale context")

        amount = _quantize_money(Decimal(digital_total))
        result = {
            "sale_id": str(sale_id),
            "branch_id": str(branch_id),
            "provider": provider,
            "provider_reference": provider_reference,
            "status": "reconciled",
            "reconciled_amount": str(amount),
            "reconciled_at": datetime.now(timezone.utc).isoformat(),
        }

        duration_ms = measure_elapsed_ms(started)
        increment_counter("sales_payment_reconcile_async_success_total", branch_id=branch_id, provider=provider)
        observe_histogram_ms("sales_payment_reconcile_async_latency_ms", duration_ms, branch_id=branch_id, provider=provider)
        log_event(
            "sales.payment_reconcile.async_success",
            request_id=request_id,
            correlation_id=request_id,
            branch_id=branch_id,
            sale_id=sale_id,
            provider=provider,
            duration_ms=f"{duration_ms:.2f}",
        )
        return result
    except Exception as exc:  # noqa: BLE001
        reason = "provider_error"
        if "match sale context" in str(exc):
            reason = "reference_mismatch"

        duration_ms = measure_elapsed_ms(started)
        increment_counter(
            "sales_payment_reconcile_async_failures_total",
            branch_id=branch_id,
            provider=provider,
            reason=reason,
        )
        observe_histogram_ms("sales_payment_reconcile_async_latency_ms", duration_ms, branch_id=branch_id, provider=provider)
        log_event(
            "sales.payment_reconcile.async_failure",
            level="error",
            request_id=request_id,
            correlation_id=request_id,
            branch_id=branch_id,
            sale_id=sale_id,
            provider=provider,
            detail=str(exc),
            duration_ms=f"{duration_ms:.2f}",
        )
        raise

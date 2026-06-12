"""Week 15 tests for durable async job foundation with Celery task wiring."""

from __future__ import annotations

from app.core.celery_app import celery_app
from app.tasks.sales_tasks import reconcile_sale_payment_task


celery_app.conf.task_always_eager = True
celery_app.conf.task_store_eager_result = True
celery_app.conf.result_backend = "cache+memory://"


def test_reconcile_task_succeeds_with_matching_reference() -> None:
    result = reconcile_sale_payment_task.delay(
        sale_id=55,
        branch_id=1,
        provider="simulated",
        provider_reference="sim-1-55-0-400-req",
        digital_total="4.00",
        request_id="req-week15-ok",
    )

    assert result.state == "SUCCESS"
    payload = result.get(timeout=1)
    assert payload["sale_id"] == "55"
    assert payload["branch_id"] == "1"
    assert payload["status"] == "reconciled"
    assert payload["reconciled_amount"] == "4.00"


def test_reconcile_task_fails_with_mismatched_reference() -> None:
    result = reconcile_sale_payment_task.delay(
        sale_id=55,
        branch_id=1,
        provider="simulated",
        provider_reference="sim-1-999-0-400-req",
        digital_total="4.00",
        request_id="req-week15-bad",
    )

    assert result.state == "FAILURE"
    assert "Provider reference does not match sale context" in str(result.result)

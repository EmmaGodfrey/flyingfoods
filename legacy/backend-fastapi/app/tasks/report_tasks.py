"""Celery tasks for report materialization."""

from __future__ import annotations

from app.core.celery_app import celery_app

PROCUREMENT_SPEND_REPORT_TASK = "app.tasks.report_tasks.build_procurement_spend_report_task"


@celery_app.task(name=PROCUREMENT_SPEND_REPORT_TASK)
def build_procurement_spend_report_task(*, branch_id: int, rows: list[dict[str, str]], request_id: str | None) -> dict[str, object]:
    return {
        "branch_id": branch_id,
        "rows": rows,
        "request_id": request_id,
    }

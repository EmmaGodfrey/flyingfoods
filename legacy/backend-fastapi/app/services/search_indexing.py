"""Search indexing enqueue helpers for product, supplier, and invoice documents."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from app.core.config import settings
from app.core.observability import log_event
from app.core.search_index import delete_search_document_sync, upsert_search_document_sync
from app.tasks.search_tasks import delete_search_document_task, index_search_document_task


def _enqueue_index_task(document_id: str, document: dict[str, object]) -> None:
    try:
        index_search_document_task.delay(document_id=document_id, document=document)
    except Exception as exc:  # noqa: BLE001
        log_event("search.index.enqueue_failed", level="warning", detail=str(exc), document_id=document_id)
        if settings.celery_task_always_eager:
            upsert_search_document_sync(document_id=document_id, document=document)


def _enqueue_delete_task(document_id: str) -> None:
    try:
        delete_search_document_task.delay(document_id=document_id)
    except Exception as exc:  # noqa: BLE001
        log_event("search.index.enqueue_delete_failed", level="warning", detail=str(exc), document_id=document_id)
        if settings.celery_task_always_eager:
            delete_search_document_sync(document_id=document_id)


def _money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01")))


def index_product_document(*, product_id: int, branch_id: int, name: str, category_id: int | None, sku: str | None, barcode: str | None, supplier_id: int | None, is_active: bool) -> None:
    document_id = f"product:{branch_id}:{product_id}"
    subtitle_parts: list[str] = []
    if sku:
        subtitle_parts.append(f"SKU {sku}")
    if barcode:
        subtitle_parts.append(f"Barcode {barcode}")

    body = " ".join(
        value
        for value in [
            sku or "",
            barcode or "",
            f"category:{category_id}" if category_id is not None else "",
            f"supplier:{supplier_id}" if supplier_id is not None else "",
        ]
        if value
    )

    _enqueue_index_task(
        document_id,
        {
            "doc_type": "product",
            "branch_id": branch_id,
            "item_id": str(product_id),
            "title": name,
            "subtitle": " | ".join(subtitle_parts) if subtitle_parts else None,
            "body": body,
            "route": f"/inventory/products/{product_id}",
            "is_active": is_active,
        },
    )


def delete_product_document(*, product_id: int, branch_id: int) -> None:
    _enqueue_delete_task(f"product:{branch_id}:{product_id}")


def index_supplier_document(*, supplier_id: int, branch_id: int, name: str, contact_name: str | None, phone: str | None, email: str | None, is_active: bool) -> None:
    document_id = f"supplier:{branch_id}:{supplier_id}"
    body = " ".join(value for value in [contact_name or "", phone or "", email or ""] if value)
    subtitle = email or phone or contact_name

    _enqueue_index_task(
        document_id,
        {
            "doc_type": "supplier",
            "branch_id": branch_id,
            "item_id": str(supplier_id),
            "title": name,
            "subtitle": subtitle,
            "body": body,
            "route": f"/procurement?supplier_id={supplier_id}",
            "is_active": is_active,
        },
    )


def delete_supplier_document(*, supplier_id: int, branch_id: int) -> None:
    _enqueue_delete_task(f"supplier:{branch_id}:{supplier_id}")


def index_invoice_document(*, sale_id: int, branch_id: int, payment_method: str, total: Decimal, created_at: datetime | None) -> None:
    document_id = f"invoice:{branch_id}:{sale_id}"
    subtitle = f"{payment_method} | total {_money(total)}"

    _enqueue_index_task(
        document_id,
        {
            "doc_type": "invoice",
            "branch_id": branch_id,
            "item_id": str(sale_id),
            "title": f"Invoice #{sale_id}",
            "subtitle": subtitle,
            "body": f"{payment_method} {_money(total)}",
            "route": f"/sales/{sale_id}/receipt",
            "created_at": created_at.isoformat() if created_at is not None else None,
            "is_active": True,
        },
    )


def delete_invoice_document(*, sale_id: int, branch_id: int) -> None:
    _enqueue_delete_task(f"invoice:{branch_id}:{sale_id}")

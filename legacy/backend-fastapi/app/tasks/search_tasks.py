"""Celery tasks for Elasticsearch indexing and backfill operations."""

from __future__ import annotations

from typing import Any

from app.core.celery_app import celery_app
from app.core.search_index import delete_search_document_sync, ensure_search_index_sync, upsert_search_document_sync

INDEX_SEARCH_DOCUMENT_TASK = "app.tasks.search_tasks.index_search_document_task"
DELETE_SEARCH_DOCUMENT_TASK = "app.tasks.search_tasks.delete_search_document_task"
ENSURE_SEARCH_INDEX_TASK = "app.tasks.search_tasks.ensure_search_index_task"


@celery_app.task(name=ENSURE_SEARCH_INDEX_TASK)
def ensure_search_index_task() -> dict[str, Any]:
    return {"ok": ensure_search_index_sync()}


@celery_app.task(name=INDEX_SEARCH_DOCUMENT_TASK)
def index_search_document_task(*, document_id: str, document: dict[str, Any]) -> dict[str, Any]:
    return {"ok": upsert_search_document_sync(document_id=document_id, document=document), "document_id": document_id}


@celery_app.task(name=DELETE_SEARCH_DOCUMENT_TASK)
def delete_search_document_task(*, document_id: str) -> dict[str, Any]:
    return {"ok": delete_search_document_sync(document_id=document_id), "document_id": document_id}

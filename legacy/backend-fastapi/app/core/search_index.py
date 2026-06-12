"""Elasticsearch helpers for search indexing and querying."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from app.core.config import settings
from app.core.observability import log_event

SEARCH_INDEX_NAME = "erp-search"


@lru_cache(maxsize=1)
def get_elasticsearch_client() -> Any | None:
    """Return an Elasticsearch client if dependency is installed and reachable by config."""
    try:
        from elasticsearch import Elasticsearch
    except Exception:
        return None

    return Elasticsearch(settings.elasticsearch_url)


@lru_cache(maxsize=1)
def get_async_elasticsearch_client() -> Any | None:
    """Return an async Elasticsearch client if dependency is installed and configured."""
    try:
        from elasticsearch import AsyncElasticsearch
    except Exception:
        return None

    return AsyncElasticsearch(settings.elasticsearch_url)


def ensure_search_index_sync() -> bool:
    """Create the search index with mappings when needed."""
    client = get_elasticsearch_client()
    if client is None:
        return False

    mappings = {
        "properties": {
            "doc_type": {"type": "keyword"},
            "branch_id": {"type": "integer"},
            "item_id": {"type": "keyword"},
            "title": {
                "type": "text",
                "fields": {
                    "raw": {"type": "keyword"},
                },
            },
            "subtitle": {"type": "text"},
            "body": {"type": "text"},
            "route": {"type": "keyword"},
            "created_at": {"type": "date"},
        }
    }

    try:
        exists = client.indices.exists(index=SEARCH_INDEX_NAME)
        if not exists:
            client.indices.create(index=SEARCH_INDEX_NAME, mappings=mappings)
    except Exception as exc:  # noqa: BLE001
        log_event("search.index.ensure_failed", level="warning", detail=str(exc))
        return False

    return True


def upsert_search_document_sync(*, document_id: str, document: dict[str, Any]) -> bool:
    """Upsert one search document into Elasticsearch."""
    client = get_elasticsearch_client()
    if client is None:
        return False
    if not ensure_search_index_sync():
        return False

    try:
        client.index(index=SEARCH_INDEX_NAME, id=document_id, document=document, refresh=False)
        return True
    except Exception as exc:  # noqa: BLE001
        log_event("search.index.upsert_failed", level="warning", detail=str(exc), document_id=document_id)
        return False


def delete_search_document_sync(*, document_id: str) -> bool:
    """Delete one search document if it exists."""
    client = get_elasticsearch_client()
    if client is None:
        return False
    if not ensure_search_index_sync():
        return False

    try:
        client.delete(index=SEARCH_INDEX_NAME, id=document_id, ignore=[404], refresh=False)
        return True
    except Exception as exc:  # noqa: BLE001
        log_event("search.index.delete_failed", level="warning", detail=str(exc), document_id=document_id)
        return False

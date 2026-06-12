"""Branch-scoped global search service across products, suppliers, and invoices."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import String, cast, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.observability import log_event
from app.core.search_index import SEARCH_INDEX_NAME, get_async_elasticsearch_client
from app.db.models import Product, Sale, Supplier
from app.schemas.search import SearchResponse, SearchResultItem


def _normalize_query(query: str) -> str:
    return query.strip()


async def search_workspace(
    session: AsyncSession,
    *,
    branch_id: int,
    query: str,
    limit_per_group: int = 8,
) -> SearchResponse:
    normalized = _normalize_query(query)
    elasticsearch_response = await _search_workspace_elasticsearch(
        branch_id=branch_id,
        query=normalized,
        limit_per_group=limit_per_group,
    )
    if elasticsearch_response is not None:
        return elasticsearch_response

    return await _search_workspace_db_fallback(
        session,
        branch_id=branch_id,
        query=normalized,
        limit_per_group=limit_per_group,
    )


def _build_es_query(*, branch_id: int, query: str, limit_per_group: int) -> dict[str, Any]:
    per_type_limit = max(1, limit_per_group)
    total_hits = per_type_limit * 3
    return {
        "size": total_hits,
        "query": {
            "bool": {
                "filter": [
                    {"term": {"branch_id": branch_id}},
                    {"term": {"is_active": True}},
                ],
                "must": [
                    {
                        "multi_match": {
                            "query": query,
                            "fields": ["title^3", "subtitle^2", "body"],
                            "fuzziness": "AUTO",
                        }
                    }
                ],
            }
        },
        "highlight": {
            "pre_tags": ["<em>"],
            "post_tags": ["</em>"],
            "fields": {
                "title": {},
                "subtitle": {},
                "body": {"fragment_size": 120, "number_of_fragments": 1},
            },
        },
        "sort": [{"_score": "desc"}],
    }


def _to_search_item(hit: dict[str, Any]) -> SearchResultItem:
    source = hit.get("_source", {})
    highlight = hit.get("highlight", {})
    fragments: list[str] = []
    for key in ("title", "subtitle", "body"):
        values = highlight.get(key, [])
        if isinstance(values, list):
            fragments.extend(str(value) for value in values if value)
    return SearchResultItem(
        item_type=str(source.get("doc_type", "")),
        item_id=str(source.get("item_id", "")),
        title=str(source.get("title", "")),
        subtitle=source.get("subtitle"),
        route=source.get("route"),
        highlights=fragments,
    )


async def _search_workspace_elasticsearch(*, branch_id: int, query: str, limit_per_group: int) -> SearchResponse | None:
    client = get_async_elasticsearch_client()
    if client is None:
        return None

    try:
        result = await client.search(index=SEARCH_INDEX_NAME, body=_build_es_query(branch_id=branch_id, query=query, limit_per_group=limit_per_group))
    except Exception as exc:  # noqa: BLE001
        log_event("search.query.elasticsearch_failed", level="warning", branch_id=branch_id, detail=str(exc))
        return None

    hits = result.get("hits", {}).get("hits", [])
    grouped: dict[str, list[SearchResultItem]] = {"product": [], "supplier": [], "invoice": []}
    for hit in hits:
        item = _to_search_item(hit)
        bucket = grouped.get(item.item_type)
        if bucket is None:
            continue
        if len(bucket) < limit_per_group:
            bucket.append(item)

    return SearchResponse(
        query=query,
        branch_id=branch_id,
        total=len(grouped["product"]) + len(grouped["supplier"]) + len(grouped["invoice"]),
        products=grouped["product"],
        suppliers=grouped["supplier"],
        invoices=grouped["invoice"],
    )


async def _search_workspace_db_fallback(
    session: AsyncSession,
    *,
    branch_id: int,
    query: str,
    limit_per_group: int,
) -> SearchResponse:
    like = f"%{query}%"

    product_rows = (
        await session.execute(
            select(Product.id, Product.name, Product.sku, Product.barcode)
            .where(Product.branch_id == branch_id, Product.name.ilike(like))
            .order_by(Product.name.asc())
            .limit(limit_per_group)
        )
    ).all()

    supplier_rows = (
        await session.execute(
            select(Supplier.id, Supplier.name, Supplier.email, Supplier.phone)
            .where(Supplier.branch_id == branch_id, Supplier.name.ilike(like))
            .order_by(Supplier.name.asc())
            .limit(limit_per_group)
        )
    ).all()

    invoice_rows = (
        await session.execute(
            select(Sale.id, Sale.total, Sale.payment_method)
            .where(
                Sale.branch_id == branch_id,
                cast(Sale.id, String).ilike(like),
            )
            .order_by(Sale.id.desc())
            .limit(limit_per_group)
        )
    ).all()

    products = [
        SearchResultItem(
            item_type="product",
            item_id=str(row.id),
            title=row.name,
            subtitle=f"SKU {row.sku}" if row.sku else (f"Barcode {row.barcode}" if row.barcode else None),
            route=f"/inventory/products/{row.id}",
        )
        for row in product_rows
    ]

    suppliers = [
        SearchResultItem(
            item_type="supplier",
            item_id=str(row.id),
            title=row.name,
            subtitle=row.email or row.phone,
            route=f"/procurement?supplier_id={row.id}",
        )
        for row in supplier_rows
    ]

    invoices = [
        SearchResultItem(
            item_type="invoice",
            item_id=str(row.id),
            title=f"Invoice #{row.id}",
            subtitle=f"{row.payment_method} | total {Decimal(row.total).quantize(Decimal('0.01'))}",
            route=f"/sales/{row.id}/receipt",
        )
        for row in invoice_rows
    ]

    return SearchResponse(
        query=query,
        branch_id=branch_id,
        total=len(products) + len(suppliers) + len(invoices),
        products=products,
        suppliers=suppliers,
        invoices=invoices,
    )

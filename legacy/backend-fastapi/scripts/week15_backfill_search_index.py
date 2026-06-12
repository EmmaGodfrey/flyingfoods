"""Backfill Elasticsearch search documents from existing ERP data."""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.core.search_index import ensure_search_index_sync
from app.db.models import Product, Sale, Supplier
from app.db.session import SessionLocal
from app.services.search_indexing import index_invoice_document, index_product_document, index_supplier_document


async def backfill() -> None:
    ensure_search_index_sync()

    async with SessionLocal() as session:
        products = (await session.execute(select(Product))).scalars().all()
        suppliers = (await session.execute(select(Supplier))).scalars().all()
        sales = (await session.execute(select(Sale))).scalars().all()

    for product in products:
        index_product_document(
            product_id=product.id,
            branch_id=product.branch_id,
            name=product.name,
            category_id=product.category_id,
            sku=product.sku,
            barcode=product.barcode,
            supplier_id=product.supplier_id,
            is_active=product.is_active,
        )

    for supplier in suppliers:
        index_supplier_document(
            supplier_id=supplier.id,
            branch_id=supplier.branch_id,
            name=supplier.name,
            contact_name=supplier.contact_name,
            phone=supplier.phone,
            email=supplier.email,
            is_active=supplier.is_active,
        )

    for sale in sales:
        index_invoice_document(
            sale_id=sale.id,
            branch_id=sale.branch_id,
            payment_method=sale.payment_method,
            total=sale.total,
            created_at=sale.created_at,
        )

    print(f"Queued indexing for {len(products)} products, {len(suppliers)} suppliers, {len(sales)} invoices")


if __name__ == "__main__":
    asyncio.run(backfill())

"""Week 15 tests for branch-scoped global search endpoint."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_user
from app.db.base import Base
from app.db.models import Branch, Product, Sale, Supplier, Unit, User
from app.db.session import get_db
from app.main import app
from app.services import search_service


def _build_test_db() -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async def _init() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_init())
    return session_factory


def _override_db(session_factory: async_sessionmaker[AsyncSession]):
    async def _get_db_override():
        async with session_factory() as session:
            yield session

    return _get_db_override


async def _manager_branch1() -> User:
    return User(
        id=10,
        email="manager@example.com",
        hashed_password="hashed",
        role="manager",
        branch_id=1,
        is_active=True,
    )


async def _manager_branch2() -> User:
    return User(
        id=20,
        email="manager2@example.com",
        hashed_password="hashed",
        role="manager",
        branch_id=2,
        is_active=True,
    )


def _seed_data(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async def _seed() -> None:
        async with session_factory() as session:
            session.add_all(
                [
                    Branch(id=1, code="HQ", name="Headquarters"),
                    Branch(id=2, code="BR2", name="Branch 2"),
                    Unit(id=1, branch_id=1, name="Piece", symbol="pc"),
                    Unit(id=2, branch_id=2, name="Piece", symbol="pc"),
                    Supplier(id=1, branch_id=1, name="Acme Foods", is_active=True),
                    Supplier(id=2, branch_id=2, name="Other Supplier", is_active=True),
                    Product(
                        id=201,
                        branch_id=1,
                        unit_id=1,
                        supplier_id=1,
                        name="Burger Bun",
                        reorder_level="2.00",
                        cost_price="0.30",
                        selling_price="0.90",
                        is_active=True,
                    ),
                    Product(
                        id=301,
                        branch_id=2,
                        unit_id=2,
                        supplier_id=2,
                        name="Other Branch Burger",
                        reorder_level="2.00",
                        cost_price="0.40",
                        selling_price="1.20",
                        is_active=True,
                    ),
                    Sale(
                        id=9001,
                        branch_id=1,
                        cashier_user_id=10,
                        payment_method="cash",
                        subtotal="5.00",
                        tax_amount="0.00",
                        discount_amount="0.00",
                        total="5.00",
                        status="completed",
                        created_at=datetime(2026, 5, 30, 10, 0, tzinfo=timezone.utc),
                    ),
                ]
            )
            await session.commit()

    asyncio.run(_seed())


def test_search_returns_products_suppliers_and_invoices_for_branch_scope() -> None:
    session_factory = _build_test_db()
    _seed_data(session_factory)

    app.dependency_overrides[get_db] = _override_db(session_factory)
    app.dependency_overrides[get_current_user] = _manager_branch1

    try:
        client = TestClient(app)

        product_query = client.get("/search", params={"q": "burger"})
        assert product_query.status_code == 200
        payload = product_query.json()
        assert payload["branch_id"] == 1
        assert payload["products"][0]["title"] == "Burger Bun"
        assert payload["suppliers"] == []

        supplier_query = client.get("/search", params={"q": "acme"})
        assert supplier_query.status_code == 200
        supplier_payload = supplier_query.json()
        assert supplier_payload["suppliers"][0]["title"] == "Acme Foods"

        invoice_query = client.get("/search", params={"q": "9001"})
        assert invoice_query.status_code == 200
        invoice_payload = invoice_query.json()
        assert invoice_payload["invoices"][0]["title"] == "Invoice #9001"
    finally:
        app.dependency_overrides.clear()


def test_search_does_not_leak_cross_branch_results() -> None:
    session_factory = _build_test_db()
    _seed_data(session_factory)

    app.dependency_overrides[get_db] = _override_db(session_factory)
    app.dependency_overrides[get_current_user] = _manager_branch2

    try:
        client = TestClient(app)
        response = client.get("/search", params={"q": "burger"})
        assert response.status_code == 200
        payload = response.json()
        assert payload["branch_id"] == 2
        assert payload["products"][0]["title"] == "Other Branch Burger"
        assert all(item["title"] != "Burger Bun" for item in payload["products"])
    finally:
        app.dependency_overrides.clear()


def test_search_uses_elasticsearch_highlights_when_available() -> None:
    session_factory = _build_test_db()
    _seed_data(session_factory)

    class _FakeAsyncElasticsearch:
        async def search(self, *, index: str, body: dict[str, object]):
            assert index == "erp-search"
            assert "multi_match" in str(body)
            return {
                "hits": {
                    "hits": [
                        {
                            "_source": {
                                "doc_type": "product",
                                "item_id": "201",
                                "title": "Burger Bun",
                                "subtitle": "SKU BUN-1",
                                "route": "/inventory/products/201",
                            },
                            "highlight": {
                                "title": ["<em>Burge</em>r Bun"],
                                "body": ["soft <em>burge</em>r bun"],
                            },
                        }
                    ]
                }
            }

    original_client_factory = search_service.get_async_elasticsearch_client
    search_service.get_async_elasticsearch_client = lambda: _FakeAsyncElasticsearch()

    app.dependency_overrides[get_db] = _override_db(session_factory)
    app.dependency_overrides[get_current_user] = _manager_branch1

    try:
        client = TestClient(app)
        response = client.get("/search", params={"q": "burge"})
        assert response.status_code == 200
        payload = response.json()
        assert payload["products"][0]["title"] == "Burger Bun"
        assert payload["products"][0]["highlights"]
        assert "<em>" in payload["products"][0]["highlights"][0]
    finally:
        search_service.get_async_elasticsearch_client = original_client_factory
        app.dependency_overrides.clear()

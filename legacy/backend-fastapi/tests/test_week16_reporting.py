"""Week 16 tests for reporting APIs and async report task contracts."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_user
from app.core.celery_app import celery_app
from app.core.redis import get_redis
from app.db.base import Base
from app.db.models import Branch, Product, Sale, SaleLineItem, StockMovement, Supplier, Unit, User
from app.db.models.procurement import GoodsReceivedNote, GoodsReceivedNoteLineItem, PurchaseOrder, PurchaseOrderLineItem
from app.db.session import get_db
from app.main import app

celery_app.conf.task_always_eager = True
celery_app.conf.task_store_eager_result = True
celery_app.conf.result_backend = "cache+memory://"


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str):
        return self.store.get(key)

    async def setex(self, key: str, _ttl: int, value: str) -> None:
        self.store[key] = value

    async def delete(self, key: str) -> None:
        self.store.pop(key, None)


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


async def _get_manager_override() -> User:
    return User(
        id=10,
        email="manager@example.com",
        hashed_password="hashed",
        role="manager",
        branch_id=1,
        is_active=True,
    )


async def _get_other_branch_manager_override() -> User:
    return User(
        id=11,
        email="manager2@example.com",
        hashed_password="hashed",
        role="manager",
        branch_id=2,
        is_active=True,
    )


def _seed_reporting_data(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async def _seed() -> None:
        async with session_factory() as session:
            session.add_all(
                [
                    Branch(id=1, code="HQ", name="Headquarters"),
                    Branch(id=2, code="B2", name="Branch 2"),
                    Unit(id=1, branch_id=1, name="Piece", symbol="pc"),
                    Unit(id=2, branch_id=2, name="Piece", symbol="pc"),
                    User(id=10, email="manager@example.com", hashed_password="hashed", role="manager", branch_id=1, is_active=True),
                    User(id=11, email="manager2@example.com", hashed_password="hashed", role="manager", branch_id=2, is_active=True),
                    Supplier(id=1, branch_id=1, name="Acme Foods", is_active=True),
                    Supplier(id=2, branch_id=1, name="Blue Farm", is_active=True),
                    Product(
                        id=201,
                        branch_id=1,
                        unit_id=1,
                        supplier_id=1,
                        name="Burger",
                        reorder_level="2.00",
                        cost_price="1.20",
                        selling_price="4.50",
                        is_active=True,
                    ),
                    Product(
                        id=202,
                        branch_id=1,
                        unit_id=1,
                        supplier_id=2,
                        name="Fries",
                        reorder_level="2.00",
                        cost_price="0.60",
                        selling_price="2.00",
                        is_active=True,
                    ),
                    Product(
                        id=301,
                        branch_id=2,
                        unit_id=2,
                        name="Branch 2 Item",
                        reorder_level="1.00",
                        cost_price="0.50",
                        selling_price="1.20",
                        is_active=True,
                    ),
                    StockMovement(
                        id=1,
                        product_id=201,
                        branch_id=1,
                        qty="20.00",
                        movement_type="receive",
                        reference_id="PO-1",
                        created_by=10,
                        created_at=datetime(2026, 5, 28, 8, 0, tzinfo=timezone.utc),
                    ),
                    StockMovement(
                        id=2,
                        product_id=202,
                        branch_id=1,
                        qty="10.00",
                        movement_type="receive",
                        reference_id="PO-2",
                        created_by=10,
                        created_at=datetime(2026, 5, 29, 8, 0, tzinfo=timezone.utc),
                    ),
                    PurchaseOrder(
                        id=100,
                        branch_id=1,
                        supplier_id=1,
                        status="closed",
                        created_by_user_id=10,
                        submitted_by_user_id=10,
                        approved_by_user_id=10,
                        created_at=datetime(2026, 5, 29, 7, 0, tzinfo=timezone.utc),
                    ),
                    PurchaseOrder(
                        id=101,
                        branch_id=1,
                        supplier_id=2,
                        status="closed",
                        created_by_user_id=10,
                        submitted_by_user_id=10,
                        approved_by_user_id=10,
                        created_at=datetime(2026, 5, 29, 7, 30, tzinfo=timezone.utc),
                    ),
                    PurchaseOrderLineItem(
                        id=1001,
                        purchase_order_id=100,
                        branch_id=1,
                        product_id=201,
                        quantity="8.00",
                        unit_price="1.20",
                        received_quantity="8.00",
                    ),
                    PurchaseOrderLineItem(
                        id=1002,
                        purchase_order_id=101,
                        branch_id=1,
                        product_id=202,
                        quantity="5.00",
                        unit_price="0.80",
                        received_quantity="5.00",
                    ),
                    GoodsReceivedNote(
                        id=500,
                        purchase_order_id=100,
                        branch_id=1,
                        received_by_user_id=10,
                        reference="GRN-500",
                        created_at=datetime(2026, 5, 29, 11, 0, tzinfo=timezone.utc),
                    ),
                    GoodsReceivedNote(
                        id=501,
                        purchase_order_id=101,
                        branch_id=1,
                        received_by_user_id=10,
                        reference="GRN-501",
                        created_at=datetime(2026, 5, 29, 12, 0, tzinfo=timezone.utc),
                    ),
                    GoodsReceivedNoteLineItem(
                        id=6001,
                        goods_received_note_id=500,
                        purchase_order_line_item_id=1001,
                        branch_id=1,
                        product_id=201,
                        quantity_received="8.00",
                    ),
                    GoodsReceivedNoteLineItem(
                        id=6002,
                        goods_received_note_id=501,
                        purchase_order_line_item_id=1002,
                        branch_id=1,
                        product_id=202,
                        quantity_received="5.00",
                    ),
                    StockMovement(
                        id=3,
                        product_id=201,
                        branch_id=1,
                        qty="-2.00",
                        movement_type="sale",
                        reference_id="sale:1",
                        created_by=10,
                        created_at=datetime(2026, 5, 29, 10, 0, tzinfo=timezone.utc),
                    ),
                    StockMovement(
                        id=4,
                        product_id=301,
                        branch_id=2,
                        qty="99.00",
                        movement_type="receive",
                        reference_id="PO-b2",
                        created_by=11,
                        created_at=datetime(2026, 5, 28, 8, 0, tzinfo=timezone.utc),
                    ),
                    Sale(
                        id=1,
                        branch_id=1,
                        cashier_user_id=10,
                        payment_method="cash",
                        subtotal="9.00",
                        tax_amount="1.00",
                        discount_amount="0.50",
                        total="9.50",
                        status="completed",
                        created_at=datetime(2026, 5, 29, 10, 0, tzinfo=timezone.utc),
                    ),
                    SaleLineItem(
                        id=1,
                        sale_id=1,
                        branch_id=1,
                        product_id=201,
                        quantity="2.00",
                        unit_price="4.50",
                        line_total="9.00",
                    ),
                ]
            )
            await session.commit()

    asyncio.run(_seed())


def test_sales_report_json_and_csv_contract() -> None:
    session_factory = _build_test_db()
    _seed_reporting_data(session_factory)

    fake_redis = FakeRedis()

    async def _get_redis_override():
        yield fake_redis

    app.dependency_overrides[get_db] = _override_db(session_factory)
    app.dependency_overrides[get_current_user] = _get_manager_override
    app.dependency_overrides[get_redis] = _get_redis_override

    try:
        client = TestClient(app)

        json_response = client.get("/reports/sales", params={"payment_method": "cash"})
        assert json_response.status_code == 200
        payload = json_response.json()
        assert payload["branch_id"] == 1
        assert payload["totals"]["sale_count"] == 1
        assert payload["totals"]["gross_total"] == "9.00"
        assert payload["lines"][0]["product_name"] == "Burger"

        csv_response = client.get("/reports/sales/export/csv", params={"payment_method": "cash"})
        assert csv_response.status_code == 200
        assert "text/csv" in csv_response.headers["content-type"]
        assert "sale_id,sold_at,cashier_user_id,payment_method,product_id,product_name,quantity,unit_price,line_total" in csv_response.text
        assert ",Burger,2.00,4.50,9.00" in csv_response.text
    finally:
        app.dependency_overrides.clear()


def test_inventory_reports_contracts() -> None:
    session_factory = _build_test_db()
    _seed_reporting_data(session_factory)

    fake_redis = FakeRedis()

    async def _get_redis_override():
        yield fake_redis

    app.dependency_overrides[get_db] = _override_db(session_factory)
    app.dependency_overrides[get_current_user] = _get_manager_override
    app.dependency_overrides[get_redis] = _get_redis_override

    try:
        client = TestClient(app)

        valuation = client.get("/reports/inventory/valuation")
        assert valuation.status_code == 200
        valuation_payload = valuation.json()
        assert valuation_payload["branch_id"] == 1
        assert valuation_payload["total_valuation"] == "27.60"

        movements = client.get("/reports/inventory/movements", params={"movement_type": "receive"})
        assert movements.status_code == 200
        movement_payload = movements.json()
        assert movement_payload["total"] == 2
        assert movement_payload["items"][0]["movement_type"] == "receive"
    finally:
        app.dependency_overrides.clear()


def test_procurement_spend_async_task_status_is_branch_scoped() -> None:
    session_factory = _build_test_db()
    _seed_reporting_data(session_factory)

    fake_redis = FakeRedis()

    async def _get_redis_override():
        yield fake_redis

    app.dependency_overrides[get_db] = _override_db(session_factory)
    app.dependency_overrides[get_current_user] = _get_manager_override
    app.dependency_overrides[get_redis] = _get_redis_override

    try:
        client = TestClient(app)
        enqueue = client.post("/reports/procurement/spend/async")
        assert enqueue.status_code == 202
        task_id = enqueue.json()["task_id"]

        status_response = client.get(f"/reports/tasks/{task_id}/status")
        assert status_response.status_code == 200
        payload = status_response.json()
        assert payload["status"] == "succeeded"
        assert payload["report_type"] == "procurement_spend"
        assert len(payload["result"]["rows"]) == 2
        row_totals = sorted(row["total_spend"] for row in payload["result"]["rows"])
        assert row_totals == ["4.00", "9.60"]

    finally:
        app.dependency_overrides.clear()

    app.dependency_overrides[get_db] = _override_db(session_factory)
    app.dependency_overrides[get_current_user] = _get_other_branch_manager_override
    app.dependency_overrides[get_redis] = _get_redis_override

    try:
        client = TestClient(app)
        denied = client.get(f"/reports/tasks/{task_id}/status")
        assert denied.status_code == 404
        assert denied.json()["detail"] == "Report task not found"
    finally:
        app.dependency_overrides.clear()

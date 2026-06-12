"""Week 10 tests for POS sales APIs, branch scoping, and sales summary contracts."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_user
from app.core.redis import get_redis
from app.db.base import Base
from app.db.models import AuditLog, BillOfMaterial, Branch, Product, StockMovement, Unit, User
from app.db.session import get_db
from app.main import app


class FakeRedis:
    def __init__(self) -> None:
        self.deleted_keys: list[str] = []

    async def get(self, _key: str):
        return None

    async def setex(self, _key: str, _ttl: int, _value: str) -> None:
        return None

    async def delete(self, key: str) -> None:
        self.deleted_keys.append(key)


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


def _seed_pos_data(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async def _seed() -> None:
        async with session_factory() as session:
            session.add_all(
                [
                    Branch(id=1, code="HQ", name="Headquarters"),
                    Branch(id=2, code="BR2", name="Branch 2"),
                    Unit(id=1, branch_id=1, name="Piece", symbol="pc"),
                    Unit(id=2, branch_id=2, name="Piece", symbol="pc"),
                    User(
                        id=10,
                        email="manager@example.com",
                        hashed_password="hashed",
                        role="manager",
                        branch_id=1,
                        is_active=True,
                    ),
                    Product(
                        id=200,
                        branch_id=1,
                        unit_id=1,
                        name="Burger Bun",
                        reorder_level="5.00",
                        cost_price="0.20",
                        selling_price="0.00",
                        is_active=True,
                    ),
                    Product(
                        id=201,
                        branch_id=1,
                        unit_id=1,
                        name="Beef Patty",
                        reorder_level="5.00",
                        cost_price="0.50",
                        selling_price="0.00",
                        is_active=True,
                    ),
                    Product(
                        id=202,
                        branch_id=1,
                        unit_id=1,
                        name="Burger",
                        reorder_level="2.00",
                        cost_price="1.20",
                        selling_price="4.50",
                        is_active=True,
                    ),
                    Product(
                        id=203,
                        branch_id=1,
                        unit_id=1,
                        name="Water Bottle",
                        reorder_level="3.00",
                        cost_price="0.30",
                        selling_price="1.00",
                        is_active=True,
                    ),
                    Product(
                        id=300,
                        branch_id=2,
                        unit_id=2,
                        name="Other Branch Item",
                        reorder_level="1.00",
                        cost_price="0.10",
                        selling_price="0.80",
                        is_active=True,
                    ),
                    BillOfMaterial(branch_id=1, product_id=202, ingredient_id=200, quantity="2.0000"),
                    BillOfMaterial(branch_id=1, product_id=202, ingredient_id=201, quantity="1.0000"),
                    StockMovement(
                        id=1,
                        product_id=200,
                        branch_id=1,
                        qty="40.00",
                        movement_type="receive",
                        reference_id="seed-bun",
                        created_by=10,
                        created_at=datetime(2026, 5, 28, 8, 0, tzinfo=timezone.utc),
                    ),
                    StockMovement(
                        id=2,
                        product_id=201,
                        branch_id=1,
                        qty="20.00",
                        movement_type="receive",
                        reference_id="seed-patty",
                        created_by=10,
                        created_at=datetime(2026, 5, 28, 8, 0, tzinfo=timezone.utc),
                    ),
                    StockMovement(
                        id=3,
                        product_id=203,
                        branch_id=1,
                        qty="10.00",
                        movement_type="receive",
                        reference_id="seed-water",
                        created_by=10,
                        created_at=datetime(2026, 5, 28, 8, 0, tzinfo=timezone.utc),
                    ),
                    StockMovement(
                        id=4,
                        product_id=300,
                        branch_id=2,
                        qty="50.00",
                        movement_type="receive",
                        reference_id="seed-branch2",
                        created_by=10,
                        created_at=datetime(2026, 5, 28, 8, 0, tzinfo=timezone.utc),
                    ),
                ]
            )
            await session.commit()

    asyncio.run(_seed())


async def _get_manager_override() -> User:
    return User(
        id=10,
        email="manager@example.com",
        hashed_password="hashed",
        role="manager",
        branch_id=1,
        is_active=True,
    )


def test_create_sale_happy_path_writes_audit_and_invalidates_cache() -> None:
    session_factory = _build_test_db()
    _seed_pos_data(session_factory)
    fake_redis = FakeRedis()

    async def _get_redis_override():
        yield fake_redis

    app.dependency_overrides[get_db] = _override_db(session_factory)
    app.dependency_overrides[get_current_user] = _get_manager_override
    app.dependency_overrides[get_redis] = _get_redis_override

    try:
        client = TestClient(app)
        response = client.post(
            "/sales",
            json={
                "payment_method": "cash",
                "items": [
                    {"product_id": 202, "quantity": "2.00"},
                    {"product_id": 203, "quantity": "1.00"},
                ],
            },
            headers={"x-request-id": "req-week10-001"},
        )

        assert response.status_code == 201
        payload = response.json()
        assert payload["branch_id"] == 1
        assert payload["payment_method"] == "cash"
        assert payload["subtotal"] == "10.00"
        assert payload["total"] == "10.00"
        assert len(payload["line_items"]) == 2

        async def _verify() -> tuple[AuditLog | None, float]:
            async with session_factory() as session:
                audit_stmt = select(AuditLog).where(AuditLog.entity_type == "sale", AuditLog.entity_id == str(payload["sale_id"]))
                audit_row = (await session.execute(audit_stmt)).scalar_one_or_none()

                stock_stmt = select(StockMovement).where(
                    StockMovement.branch_id == 1,
                    StockMovement.product_id == 200,
                    StockMovement.reference_id == f"sale:{payload['sale_id']}",
                )
                movements = (await session.execute(stock_stmt)).scalars().all()
                return audit_row, sum(float(m.qty) for m in movements)

        audit_row, bun_delta = asyncio.run(_verify())
        assert audit_row is not None
        assert audit_row.action == "sale.create"
        assert audit_row.request_id == "req-week10-001"
        assert bun_delta == -4.0
        assert fake_redis.deleted_keys == ["inventory:stock:branch:1"]
    finally:
        app.dependency_overrides.clear()


def test_create_sale_rejects_when_bom_stock_insufficient() -> None:
    session_factory = _build_test_db()
    _seed_pos_data(session_factory)
    fake_redis = FakeRedis()

    async def _get_redis_override():
        yield fake_redis

    app.dependency_overrides[get_db] = _override_db(session_factory)
    app.dependency_overrides[get_current_user] = _get_manager_override
    app.dependency_overrides[get_redis] = _get_redis_override

    try:
        client = TestClient(app)
        response = client.post(
            "/sales",
            json={
                "payment_method": "card",
                "items": [{"product_id": 202, "quantity": "25.00"}],
            },
        )
        assert response.status_code == 400
        assert "Insufficient stock" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_create_sale_rejects_branch_mismatch_products() -> None:
    session_factory = _build_test_db()
    _seed_pos_data(session_factory)
    fake_redis = FakeRedis()

    async def _get_redis_override():
        yield fake_redis

    app.dependency_overrides[get_db] = _override_db(session_factory)
    app.dependency_overrides[get_current_user] = _get_manager_override
    app.dependency_overrides[get_redis] = _get_redis_override

    try:
        client = TestClient(app)
        response = client.post(
            "/sales",
            json={
                "payment_method": "mobile",
                "items": [{"product_id": 300, "quantity": "1.00"}],
            },
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Product not found in current branch"
    finally:
        app.dependency_overrides.clear()


def test_receipt_and_daily_summary_are_branch_scoped_and_correct() -> None:
    session_factory = _build_test_db()
    _seed_pos_data(session_factory)
    fake_redis = FakeRedis()

    async def _get_redis_override():
        yield fake_redis

    app.dependency_overrides[get_db] = _override_db(session_factory)
    app.dependency_overrides[get_current_user] = _get_manager_override
    app.dependency_overrides[get_redis] = _get_redis_override

    try:
        client = TestClient(app)

        first = client.post(
            "/sales",
            json={
                "payment_method": "cash",
                "items": [{"product_id": 202, "quantity": "1.00"}],
            },
        )
        assert first.status_code == 201
        first_sale_id = first.json()["sale_id"]

        second = client.post(
            "/sales",
            json={
                "payment_method": "card",
                "items": [{"product_id": 203, "quantity": "3.00"}],
            },
        )
        assert second.status_code == 201

        receipt = client.get(f"/sales/{first_sale_id}/receipt")
        assert receipt.status_code == 200
        receipt_payload = receipt.json()
        assert receipt_payload["sale_id"] == first_sale_id
        assert receipt_payload["line_items"][0]["line_total"] == "4.50"

        summary = client.get("/sales/summary/daily")
        assert summary.status_code == 200
        summary_payload = summary.json()
        assert summary_payload["branch_id"] == 1
        assert summary_payload["sales_count"] == 2
        assert summary_payload["gross_total"] == "7.50"
        assert summary_payload["payment_method_totals"]["cash"] == "4.50"
        assert summary_payload["payment_method_totals"]["card"] == "3.00"
    finally:
        app.dependency_overrides.clear()

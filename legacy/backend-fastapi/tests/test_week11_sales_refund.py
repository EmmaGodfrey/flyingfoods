"""Week 11 tests for sales refund workflow contracts."""

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
from app.db.models import AuditLog, BillOfMaterial, Branch, Product, Sale, StockMovement, Unit, User
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


def _seed_pos_sale_data(session_factory: async_sessionmaker[AsyncSession]) -> None:
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
                    BillOfMaterial(branch_id=1, product_id=202, ingredient_id=200, quantity="2.0000"),
                    BillOfMaterial(branch_id=1, product_id=202, ingredient_id=201, quantity="1.0000"),
                    StockMovement(
                        id=1,
                        product_id=200,
                        branch_id=1,
                        qty="20.00",
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
                ]
            )
            await session.commit()

    asyncio.run(_seed())


def _create_sale(client: TestClient) -> int:
    response = client.post(
        "/sales",
        json={"payment_method": "cash", "items": [{"product_id": 202, "quantity": "2.00"}]},
        headers={"x-request-id": "req-week11-refund-sale"},
    )
    assert response.status_code == 201
    return int(response.json()["sale_id"])


def test_refund_sale_reverses_stock_emits_audit_and_invalidates_cache() -> None:
    session_factory = _build_test_db()
    _seed_pos_sale_data(session_factory)
    fake_redis = FakeRedis()

    async def _get_redis_override():
        yield fake_redis

    app.dependency_overrides[get_db] = _override_db(session_factory)
    app.dependency_overrides[get_current_user] = _get_manager_override
    app.dependency_overrides[get_redis] = _get_redis_override

    try:
        client = TestClient(app)
        sale_id = _create_sale(client)

        refund_response = client.post(
            f"/sales/{sale_id}/refund",
            json={"reason": "customer return"},
            headers={"x-request-id": "req-week11-refund"},
        )
        assert refund_response.status_code == 200
        payload = refund_response.json()
        assert payload["sale_id"] == sale_id
        assert payload["status"] == "refunded"

        async def _verify() -> tuple[Sale | None, float, float, AuditLog | None]:
            async with session_factory() as session:
                sale = (await session.execute(select(Sale).where(Sale.id == sale_id))).scalar_one_or_none()
                bun_total = (
                    await session.execute(
                        select(StockMovement).where(StockMovement.branch_id == 1, StockMovement.product_id == 200)
                    )
                ).scalars().all()
                patty_total = (
                    await session.execute(
                        select(StockMovement).where(StockMovement.branch_id == 1, StockMovement.product_id == 201)
                    )
                ).scalars().all()
                audit_row = (
                    await session.execute(
                        select(AuditLog).where(AuditLog.entity_type == "sale", AuditLog.entity_id == str(sale_id), AuditLog.action == "sale.refund")
                    )
                ).scalar_one_or_none()
                return sale, sum(float(m.qty) for m in bun_total), sum(float(m.qty) for m in patty_total), audit_row

        sale_row, bun_stock, patty_stock, audit_row = asyncio.run(_verify())
        assert sale_row is not None
        assert sale_row.status == "refunded"
        assert bun_stock == 20.0
        assert patty_stock == 20.0
        assert audit_row is not None
        assert fake_redis.deleted_keys.count("inventory:stock:branch:1") == 2
    finally:
        app.dependency_overrides.clear()


def test_refund_sale_denies_cross_branch_access() -> None:
    session_factory = _build_test_db()
    _seed_pos_sale_data(session_factory)

    async def _get_redis_override():
        yield FakeRedis()

    app.dependency_overrides[get_db] = _override_db(session_factory)
    app.dependency_overrides[get_current_user] = _get_manager_override
    app.dependency_overrides[get_redis] = _get_redis_override

    try:
        client = TestClient(app)
        sale_id = _create_sale(client)
    finally:
        app.dependency_overrides.clear()

    app.dependency_overrides[get_db] = _override_db(session_factory)
    app.dependency_overrides[get_current_user] = _get_other_branch_manager_override
    app.dependency_overrides[get_redis] = _get_redis_override

    try:
        client = TestClient(app)
        response = client.post(f"/sales/{sale_id}/refund", json={"reason": "x"})
        assert response.status_code == 404
        assert response.json()["detail"] == "Sale not found"
    finally:
        app.dependency_overrides.clear()


def test_refund_sale_rejects_duplicate_refund() -> None:
    session_factory = _build_test_db()
    _seed_pos_sale_data(session_factory)

    async def _get_redis_override():
        yield FakeRedis()

    app.dependency_overrides[get_db] = _override_db(session_factory)
    app.dependency_overrides[get_current_user] = _get_manager_override
    app.dependency_overrides[get_redis] = _get_redis_override

    try:
        client = TestClient(app)
        sale_id = _create_sale(client)

        first = client.post(f"/sales/{sale_id}/refund", json={"reason": "return"})
        assert first.status_code == 200

        second = client.post(f"/sales/{sale_id}/refund", json={"reason": "return"})
        assert second.status_code == 400
        assert second.json()["detail"] == "Sale already refunded"
    finally:
        app.dependency_overrides.clear()


def test_refund_sale_rejects_after_void() -> None:
    session_factory = _build_test_db()
    _seed_pos_sale_data(session_factory)

    async def _get_redis_override():
        yield FakeRedis()

    app.dependency_overrides[get_db] = _override_db(session_factory)
    app.dependency_overrides[get_current_user] = _get_manager_override
    app.dependency_overrides[get_redis] = _get_redis_override

    try:
        client = TestClient(app)
        sale_id = _create_sale(client)

        void_resp = client.post(f"/sales/{sale_id}/void", json={"reason": "mistake"})
        assert void_resp.status_code == 200

        refund_resp = client.post(f"/sales/{sale_id}/refund", json={"reason": "return"})
        assert refund_resp.status_code == 400
        assert refund_resp.json()["detail"] == "Sale cannot be refunded from current status"
    finally:
        app.dependency_overrides.clear()

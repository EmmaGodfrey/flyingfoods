"""Week 12 tests for sales pricing and tender contract behavior."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_user
from app.core.redis import get_redis
from app.db.base import Base
from app.db.models import BillOfMaterial, Branch, Product, StockMovement, Unit, User
from app.db.session import get_db
from app.main import app


class FakeRedis:
    async def get(self, _key: str):
        return None

    async def setex(self, _key: str, _ttl: int, _value: str) -> None:
        return None

    async def delete(self, _key: str) -> None:
        return None


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


def _seed_pos_data(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async def _seed() -> None:
        async with session_factory() as session:
            session.add_all(
                [
                    Branch(id=1, code="HQ", name="Headquarters"),
                    Unit(id=1, branch_id=1, name="Piece", symbol="pc"),
                    User(
                        id=10,
                        email="manager@example.com",
                        hashed_password="hashed",
                        role="manager",
                        branch_id=1,
                        is_active=True,
                    ),
                    Product(
                        id=201,
                        branch_id=1,
                        unit_id=1,
                        name="Bun",
                        reorder_level="2.00",
                        cost_price="0.40",
                        selling_price="0.75",
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
                    BillOfMaterial(branch_id=1, product_id=202, ingredient_id=201, quantity="2.0000"),
                    StockMovement(
                        id=1,
                        product_id=201,
                        branch_id=1,
                        qty="20.00",
                        movement_type="receive",
                        reference_id="seed-burger",
                        created_by=10,
                        created_at=datetime(2026, 5, 28, 8, 0, tzinfo=timezone.utc),
                    ),
                ]
            )
            await session.commit()

    asyncio.run(_seed())


def test_create_sale_applies_tax_discount_and_split_tenders() -> None:
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
                "payment_method": "split",
                "tax_amount": "1.00",
                "discount_amount": "0.50",
                "split_tenders": [
                    {"payment_method": "cash", "amount": "5.00"},
                    {"payment_method": "card", "amount": "4.50"},
                ],
                "items": [{"product_id": 202, "quantity": "2.00"}],
            },
            headers={"x-request-id": "req-week12-001"},
        )

        assert response.status_code == 201
        payload = response.json()
        assert payload["subtotal"] == "9.00"
        assert payload["tax_amount"] == "1.00"
        assert payload["discount_amount"] == "0.50"
        assert payload["total"] == "9.50"
        assert payload["payment_method"] == "split"
        assert payload["payment_tenders"] == [
            {"payment_method": "cash", "amount": "5.00"},
            {"payment_method": "card", "amount": "4.50"},
        ]
    finally:
        app.dependency_overrides.clear()


def test_create_sale_rejects_split_tender_mismatch() -> None:
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
                "payment_method": "split",
                "tax_amount": "1.00",
                "discount_amount": "0.50",
                "split_tenders": [
                    {"payment_method": "cash", "amount": "5.00"},
                    {"payment_method": "card", "amount": "4.00"},
                ],
                "items": [{"product_id": 202, "quantity": "2.00"}],
            },
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Split tenders must sum to total"
    finally:
        app.dependency_overrides.clear()


def test_create_sale_rejects_negative_discount() -> None:
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
                "tax_amount": "1.00",
                "discount_amount": "-0.50",
                "items": [{"product_id": 202, "quantity": "2.00"}],
            },
        )

        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()

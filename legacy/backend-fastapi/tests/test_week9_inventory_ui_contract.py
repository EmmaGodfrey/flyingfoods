"""Week 9 backend contract tests used by the inventory frontend pages."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_user
from app.core.redis import get_redis
from app.db.base import Base
from app.db.models import Branch, Product, StockMovement, Unit, User
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


def _seed_inventory_data(session_factory: async_sessionmaker[AsyncSession]) -> None:
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
                        id=200,
                        branch_id=1,
                        unit_id=1,
                        name="Widget",
                        reorder_level="5.00",
                        cost_price="2.00",
                        selling_price="3.50",
                        is_active=True,
                    ),
                    StockMovement(
                        id=1,
                        product_id=200,
                        branch_id=1,
                        qty="15.00",
                        movement_type="receive",
                        reference_id="PO-1",
                        created_by=10,
                        created_at=datetime(2026, 5, 28, 8, 0, tzinfo=timezone.utc),
                    ),
                    StockMovement(
                        id=2,
                        product_id=200,
                        branch_id=1,
                        qty="-2.00",
                        movement_type="waste",
                        reference_id="WASTE-1",
                        created_by=10,
                        created_at=datetime(2026, 5, 28, 9, 0, tzinfo=timezone.utc),
                    ),
                ]
            )
            await session.commit()

    asyncio.run(_seed())


async def _get_user_override() -> User:
    return User(
        id=10,
        email="manager@example.com",
        hashed_password="hashed",
        role="manager",
        branch_id=1,
        is_active=True,
    )


async def _get_redis_override():
    yield FakeRedis()


def test_movement_history_supports_filters_and_ordering() -> None:
    session_factory = _build_test_db()
    _seed_inventory_data(session_factory)

    app.dependency_overrides[get_db] = _override_db(session_factory)
    app.dependency_overrides[get_current_user] = _get_user_override
    app.dependency_overrides[get_redis] = _get_redis_override

    try:
        client = TestClient(app)

        response = client.get("/inventory/movements", params={"limit": 50, "offset": 0, "movement_type": "waste"})
        assert response.status_code == 200

        payload = response.json()
        assert payload["total"] == 1
        assert payload["items"][0]["movement_type"] == "waste"
        assert payload["items"][0]["created_at"].startswith("2026-05-28T09:00:00")

        by_date = client.get(
            "/inventory/movements",
            params={"occurred_after": "2026-05-28T08:30:00+00:00", "occurred_before": "2026-05-28T09:30:00+00:00"},
        )
        assert by_date.status_code == 200
        assert by_date.json()["total"] == 1

        invalid = client.get("/inventory/movements", params={"movement_type": "invalid"})
        assert invalid.status_code == 400
    finally:
        app.dependency_overrides.clear()

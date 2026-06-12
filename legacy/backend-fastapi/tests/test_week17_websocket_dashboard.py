"""Week 17 tests for live dashboard websocket contracts and broadcasts."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.redis import get_redis
from app.db.base import Base
from app.db.models import Branch, Product, StockMovement, Unit, User
from app.db.session import get_db
from app.main import app
from app.services.security import create_token


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


def _seed_data(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async def _seed() -> None:
        async with session_factory() as session:
            session.add_all(
                [
                    Branch(id=1, code="HQ", name="Headquarters"),
                    Unit(id=1, branch_id=1, name="Piece", symbol="pc"),
                    User(id=10, email="manager@example.com", hashed_password="hashed", role="manager", branch_id=1, is_active=True),
                    Product(
                        id=201,
                        branch_id=1,
                        unit_id=1,
                        name="Widget",
                        reorder_level="2.00",
                        cost_price="1.00",
                        selling_price="3.00",
                        is_active=True,
                    ),
                    StockMovement(
                        id=1,
                        product_id=201,
                        branch_id=1,
                        qty="10.00",
                        movement_type="receive",
                        reference_id="seed",
                        created_by=10,
                        created_at=datetime(2026, 5, 30, 8, 0, tzinfo=timezone.utc),
                    ),
                ]
            )
            await session.commit()

    asyncio.run(_seed())


def _access_token_for(user_id: int, branch_id: int) -> str:
    return create_token(
        subject=str(user_id),
        token_type="access",
        settings=settings,
        expires_delta=timedelta(minutes=15),
        extra_claims={"role": "manager", "branch_id": branch_id, "email": "manager@example.com"},
    )


def test_dashboard_websocket_receives_domain_and_anomaly_events() -> None:
    session_factory = _build_test_db()
    _seed_data(session_factory)

    fake_redis = FakeRedis()

    async def _get_redis_override():
        yield fake_redis

    app.dependency_overrides[get_db] = _override_db(session_factory)
    app.dependency_overrides[get_current_user] = _get_manager_override
    app.dependency_overrides[get_redis] = _get_redis_override

    try:
        client = TestClient(app)
        token = _access_token_for(user_id=10, branch_id=1)

        with client.websocket_connect(f"/ws/dashboard?token={token}") as websocket:
            connected = websocket.receive_json()
            assert connected["type"] == "connection"
            assert connected["status"] == "connected"
            assert connected["branch_id"] == 1

            sale_response = client.post(
                "/sales",
                json={"payment_method": "cash", "items": [{"product_id": 201, "quantity": "1.00"}]},
                headers={"x-request-id": "req-week17-sale"},
            )
            assert sale_response.status_code == 201
            sale_id = int(sale_response.json()["sale_id"])

            event_message = websocket.receive_json()
            assert event_message["type"] == "domain_event"
            assert event_message["action"] == "sale.create"

            void_response = client.post(
                f"/sales/{sale_id}/void",
                json={"reason": "test void"},
                headers={"x-request-id": "req-week17-void"},
            )
            assert void_response.status_code == 200

            void_event = websocket.receive_json()
            alert_event = websocket.receive_json()
            assert void_event["type"] == "domain_event"
            assert void_event["action"] == "sale.void"
            assert alert_event["type"] == "anomaly_alert"
            assert "unusual sale.void" in alert_event["message"]
    finally:
        app.dependency_overrides.clear()

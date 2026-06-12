"""Integration tests for week 6 audit hardening scenarios."""

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
from app.db.models import AuditLog, Branch, Unit, User
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


def _seed_identity_data(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async def _seed() -> None:
        async with session_factory() as session:
            branch_1 = Branch(id=1, code="HQ", name="Headquarters")
            branch_2 = Branch(id=2, code="BR2", name="Branch Two")

            unit_1 = Unit(id=1, branch_id=1, name="Piece", symbol="pc")
            unit_2 = Unit(id=2, branch_id=2, name="Piece", symbol="pc")

            manager = User(
                id=10,
                email="manager@example.com",
                hashed_password="hashed",
                role="manager",
                branch_id=1,
                is_active=True,
            )
            admin = User(
                id=11,
                email="admin@example.com",
                hashed_password="hashed",
                role="admin",
                branch_id=1,
                is_active=True,
            )

            session.add_all([branch_1, branch_2, unit_1, unit_2, manager, admin])
            await session.commit()

    asyncio.run(_seed())


def _override_db(session_factory: async_sessionmaker[AsyncSession]):
    async def _get_db_override():
        async with session_factory() as session:
            yield session

    return _get_db_override


def test_inventory_write_creates_audit_log_row() -> None:
    session_factory = _build_test_db()
    _seed_identity_data(session_factory)

    fake_redis = FakeRedis()

    async def _get_redis_override():
        yield fake_redis

    async def _get_manager_override() -> User:
        return User(
            id=10,
            email="manager@example.com",
            hashed_password="hashed",
            role="manager",
            branch_id=1,
            is_active=True,
        )

    app.dependency_overrides[get_db] = _override_db(session_factory)
    app.dependency_overrides[get_redis] = _get_redis_override
    app.dependency_overrides[get_current_user] = _get_manager_override

    try:
        client = TestClient(app)
        response = client.post(
            "/inventory/products",
            json={
                "name": "Audit Test Product",
                "unit_id": 1,
                "category_id": None,
                "supplier_id": None,
                "sku": "AUD-001",
                "barcode": None,
                "reorder_level": "5.00",
                "cost_price": "2.00",
                "selling_price": "4.00",
            },
            headers={"x-request-id": "req-week6-001"},
        )

        assert response.status_code == 201
        product_id = response.json()["id"]

        async def _verify() -> AuditLog | None:
            async with session_factory() as session:
                stmt = select(AuditLog).where(AuditLog.entity_type == "product", AuditLog.entity_id == str(product_id))
                return (await session.execute(stmt)).scalar_one_or_none()

        audit_row = asyncio.run(_verify())
        assert audit_row is not None
        assert audit_row.action == "product.create"
        assert audit_row.branch_id == 1
        assert audit_row.actor_user_id == 10
        assert audit_row.request_id == "req-week6-001"
        assert audit_row.hash_chain_curr
        assert fake_redis.deleted_keys == ["inventory:stock:branch:1"]
    finally:
        app.dependency_overrides.clear()


def test_audit_query_denies_cross_branch_for_manager() -> None:
    session_factory = _build_test_db()
    _seed_identity_data(session_factory)

    async def _get_manager_override() -> User:
        return User(
            id=10,
            email="manager@example.com",
            hashed_password="hashed",
            role="manager",
            branch_id=1,
            is_active=True,
        )

    app.dependency_overrides[get_db] = _override_db(session_factory)
    app.dependency_overrides[get_current_user] = _get_manager_override

    try:
        client = TestClient(app)
        response = client.get("/audit/logs", params={"branch_id": 2})
        assert response.status_code == 403
        assert response.json()["detail"] == "Cross-branch audit access denied"
    finally:
        app.dependency_overrides.clear()


def test_audit_query_order_and_pagination_are_deterministic() -> None:
    session_factory = _build_test_db()
    _seed_identity_data(session_factory)

    async def _get_admin_override() -> User:
        return User(
            id=11,
            email="admin@example.com",
            hashed_password="hashed",
            role="admin",
            branch_id=1,
            is_active=True,
        )

    async def _seed_logs() -> None:
        same_time = datetime(2026, 5, 28, 12, 0, 0, tzinfo=timezone.utc)
        async with session_factory() as session:
            session.add_all(
                [
                    AuditLog(
                        occurred_at=same_time,
                        actor_user_id=11,
                        branch_id=1,
                        action="product.create",
                        entity_type="product",
                        entity_id="100",
                        before_json=None,
                        after_json={"id": 100},
                        request_id="req-1",
                        source="api",
                        schema_version=1,
                        hash_chain_prev=None,
                        hash_chain_curr="a" * 64,
                    ),
                    AuditLog(
                        occurred_at=same_time,
                        actor_user_id=11,
                        branch_id=1,
                        action="product.update",
                        entity_type="product",
                        entity_id="101",
                        before_json={"id": 101},
                        after_json={"id": 101, "name": "Updated"},
                        request_id="req-2",
                        source="api",
                        schema_version=1,
                        hash_chain_prev="a" * 64,
                        hash_chain_curr="b" * 64,
                    ),
                    AuditLog(
                        occurred_at=same_time,
                        actor_user_id=11,
                        branch_id=1,
                        action="product.delete",
                        entity_type="product",
                        entity_id="102",
                        before_json={"id": 102},
                        after_json=None,
                        request_id="req-3",
                        source="api",
                        schema_version=1,
                        hash_chain_prev="b" * 64,
                        hash_chain_curr="c" * 64,
                    ),
                ]
            )
            await session.commit()

    asyncio.run(_seed_logs())

    app.dependency_overrides[get_db] = _override_db(session_factory)
    app.dependency_overrides[get_current_user] = _get_admin_override

    try:
        client = TestClient(app)
        response = client.get("/audit/logs", params={"limit": 2, "offset": 1, "branch_id": 1})
        assert response.status_code == 200

        payload = response.json()
        assert payload["total"] == 3
        assert payload["limit"] == 2
        assert payload["offset"] == 1

        # With same occurred_at timestamps, tie-breaker is id desc.
        returned_entity_ids = [item["entity_id"] for item in payload["items"]]
        assert returned_entity_ids == ["101", "100"]
    finally:
        app.dependency_overrides.clear()

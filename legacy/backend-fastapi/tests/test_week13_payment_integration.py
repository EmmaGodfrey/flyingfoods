"""Week 13 tests for payment-provider abstraction and reconciliation contracts."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import time

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_user
from app.core.celery_app import celery_app
from app.core.redis import get_redis
from app.db.base import Base
from app.db.models import AuditLog, BillOfMaterial, Branch, Product, StockMovement, Unit, User
from app.db.session import get_db
from app.main import app

celery_app.conf.task_always_eager = True
celery_app.conf.task_store_eager_result = True
celery_app.conf.result_backend = "cache+memory://"


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
                        created_at=datetime(2026, 5, 29, 8, 0, tzinfo=timezone.utc),
                    ),
                    StockMovement(
                        id=2,
                        product_id=201,
                        branch_id=1,
                        qty="20.00",
                        movement_type="receive",
                        reference_id="seed-patty",
                        created_by=10,
                        created_at=datetime(2026, 5, 29, 8, 0, tzinfo=timezone.utc),
                    ),
                ]
            )
            await session.commit()

    asyncio.run(_seed())


def _create_split_sale(client: TestClient) -> int:
    response = client.post(
        "/sales",
        json={
            "payment_method": "split",
            "split_tenders": [
                {"payment_method": "cash", "amount": "5.00"},
                {"payment_method": "card", "amount": "4.00"},
            ],
            "items": [{"product_id": 202, "quantity": "2.00"}],
        },
        headers={"x-request-id": "req-week13-sale"},
    )
    assert response.status_code == 201
    return int(response.json()["sale_id"])


def _create_cash_sale(client: TestClient) -> int:
    response = client.post(
        "/sales",
        json={"payment_method": "cash", "items": [{"product_id": 202, "quantity": "2.00"}]},
        headers={"x-request-id": "req-week13-cash"},
    )
    assert response.status_code == 201
    return int(response.json()["sale_id"])


def test_payment_intent_and_reconcile_contract_without_new_write_side_effects() -> None:
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
        sale_id = _create_split_sale(client)
        assert fake_redis.deleted_keys.count("inventory:stock:branch:1") == 1

        async def _sale_audit_count() -> int:
            async with session_factory() as session:
                return int(
                    (
                        await session.execute(
                            select(func.count(AuditLog.id)).where(
                                AuditLog.entity_type == "sale",
                                AuditLog.entity_id == str(sale_id),
                            )
                        )
                    ).scalar_one()
                    or 0
                )

        initial_audit_count = asyncio.run(_sale_audit_count())
        assert initial_audit_count == 1

        intent_response = client.post(
            f"/sales/{sale_id}/payments/intent",
            json={"provider": "simulated"},
            headers={"x-request-id": "req-week13-intent"},
        )
        assert intent_response.status_code == 200
        intent_payload = intent_response.json()
        assert intent_payload["sale_id"] == sale_id
        assert intent_payload["provider"] == "simulated"
        assert len(intent_payload["authorized_tenders"]) == 1
        authorized_tender = intent_payload["authorized_tenders"][0]
        assert authorized_tender["payment_method"] == "card"
        assert authorized_tender["amount"] == "4.00"
        assert authorized_tender["status"] == "authorized"

        reconcile_response = client.post(
            f"/sales/{sale_id}/payments/reconcile",
            json={"provider": "simulated", "provider_reference": authorized_tender["provider_reference"]},
            headers={"x-request-id": "req-week13-reconcile"},
        )
        assert reconcile_response.status_code == 200
        reconcile_payload = reconcile_response.json()
        assert reconcile_payload["sale_id"] == sale_id
        assert reconcile_payload["provider"] == "simulated"
        assert reconcile_payload["status"] == "reconciled"
        assert reconcile_payload["reconciled_amount"] == "4.00"

        final_audit_count = asyncio.run(_sale_audit_count())
        assert final_audit_count == initial_audit_count
        assert fake_redis.deleted_keys.count("inventory:stock:branch:1") == 1
    finally:
        app.dependency_overrides.clear()


def test_payment_intent_denies_cross_branch_access() -> None:
    session_factory = _build_test_db()
    _seed_pos_sale_data(session_factory)

    async def _get_redis_override():
        yield FakeRedis()

    app.dependency_overrides[get_db] = _override_db(session_factory)
    app.dependency_overrides[get_current_user] = _get_manager_override
    app.dependency_overrides[get_redis] = _get_redis_override

    try:
        client = TestClient(app)
        sale_id = _create_split_sale(client)
    finally:
        app.dependency_overrides.clear()

    app.dependency_overrides[get_db] = _override_db(session_factory)
    app.dependency_overrides[get_current_user] = _get_other_branch_manager_override
    app.dependency_overrides[get_redis] = _get_redis_override

    try:
        client = TestClient(app)
        response = client.post(f"/sales/{sale_id}/payments/intent", json={"provider": "simulated"})
        assert response.status_code == 404
        assert response.json()["detail"] == "Sale not found"
    finally:
        app.dependency_overrides.clear()


def test_payment_intent_rejects_cash_only_sale() -> None:
    session_factory = _build_test_db()
    _seed_pos_sale_data(session_factory)

    async def _get_redis_override():
        yield FakeRedis()

    app.dependency_overrides[get_db] = _override_db(session_factory)
    app.dependency_overrides[get_current_user] = _get_manager_override
    app.dependency_overrides[get_redis] = _get_redis_override

    try:
        client = TestClient(app)
        sale_id = _create_cash_sale(client)

        response = client.post(f"/sales/{sale_id}/payments/intent", json={"provider": "simulated"})
        assert response.status_code == 400
        assert response.json()["detail"] == "Sale has no provider-eligible tenders"
    finally:
        app.dependency_overrides.clear()


def test_async_payment_reconcile_job_succeeds_with_polling() -> None:
    session_factory = _build_test_db()
    _seed_pos_sale_data(session_factory)

    async def _get_redis_override():
        yield FakeRedis()

    app.dependency_overrides[get_db] = _override_db(session_factory)
    app.dependency_overrides[get_current_user] = _get_manager_override
    app.dependency_overrides[get_redis] = _get_redis_override

    try:
        client = TestClient(app)
        sale_id = _create_split_sale(client)

        intent_response = client.post(
            f"/sales/{sale_id}/payments/intent",
            json={"provider": "simulated"},
            headers={"x-request-id": "req-week13-async-intent"},
        )
        assert intent_response.status_code == 200
        provider_reference = intent_response.json()["authorized_tenders"][0]["provider_reference"]

        enqueue_response = client.post(
            f"/sales/{sale_id}/payments/reconcile/async",
            json={"provider": "simulated", "provider_reference": provider_reference},
            headers={"x-request-id": "req-week13-async-enqueue"},
        )
        assert enqueue_response.status_code == 202
        enqueue_payload = enqueue_response.json()
        assert enqueue_payload["status"] == "queued"
        job_id = enqueue_payload["job_id"]

        final_payload = None
        for _ in range(20):
            status_response = client.get(f"/sales/{sale_id}/payments/reconcile/jobs/{job_id}")
            assert status_response.status_code == 200
            payload = status_response.json()
            if payload["status"] in {"succeeded", "failed"}:
                final_payload = payload
                break
            time.sleep(0.01)

        assert final_payload is not None
        assert final_payload["status"] == "succeeded"
        assert final_payload["result"] is not None
        assert final_payload["result"]["status"] == "reconciled"
        assert final_payload["result"]["reconciled_amount"] == "4.00"
    finally:
        app.dependency_overrides.clear()


def test_async_payment_reconcile_job_records_failure_for_reference_mismatch() -> None:
    session_factory = _build_test_db()
    _seed_pos_sale_data(session_factory)

    async def _get_redis_override():
        yield FakeRedis()

    app.dependency_overrides[get_db] = _override_db(session_factory)
    app.dependency_overrides[get_current_user] = _get_manager_override
    app.dependency_overrides[get_redis] = _get_redis_override

    try:
        client = TestClient(app)
        sale_id = _create_split_sale(client)

        enqueue_response = client.post(
            f"/sales/{sale_id}/payments/reconcile/async",
            json={"provider": "simulated", "provider_reference": "sim-1-9999-bad"},
            headers={"x-request-id": "req-week13-async-bad-ref"},
        )
        assert enqueue_response.status_code == 202
        job_id = enqueue_response.json()["job_id"]

        final_payload = None
        for _ in range(20):
            status_response = client.get(f"/sales/{sale_id}/payments/reconcile/jobs/{job_id}")
            assert status_response.status_code == 200
            payload = status_response.json()
            if payload["status"] in {"succeeded", "failed"}:
                final_payload = payload
                break
            time.sleep(0.01)

        assert final_payload is not None
        assert final_payload["status"] == "failed"
        assert final_payload["result"] is None
        assert final_payload["error"] == "Provider reference does not match sale context"
    finally:
        app.dependency_overrides.clear()

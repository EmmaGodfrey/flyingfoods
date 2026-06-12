"""Week 6 tests for procurement workflow, goods receipts, and reporting."""

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
from app.db.models import AuditLog, Branch, Product, StockMovement, Supplier, Unit, User
from app.db.models.procurement import GoodsReceivedNote, PurchaseOrder
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


def _user_override(*, user_id: int, role: str, branch_id: int):
    async def _override() -> User:
        return User(
            id=user_id,
            email=f"{role}-{user_id}@example.com",
            hashed_password="hashed",
            role=role,
            branch_id=branch_id,
            is_active=True,
        )

    return _override


def _seed_procurement_data(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async def _seed() -> None:
        async with session_factory() as session:
            session.add_all(
                [
                    Branch(id=1, code="HQ", name="Headquarters"),
                    Branch(id=2, code="B2", name="Branch 2"),
                    Unit(id=1, branch_id=1, name="Piece", symbol="pc"),
                    Unit(id=2, branch_id=2, name="Piece", symbol="pc"),
                    User(id=10, email="manager@example.com", hashed_password="hashed", role="manager", branch_id=1, is_active=True),
                    User(id=20, email="admin@example.com", hashed_password="hashed", role="admin", branch_id=1, is_active=True),
                    User(id=30, email="manager2@example.com", hashed_password="hashed", role="manager", branch_id=2, is_active=True),
                    Supplier(id=1, branch_id=1, name="Acme Foods", is_active=True),
                    Supplier(id=2, branch_id=2, name="Branch 2 Supplier", is_active=True),
                    Product(
                        id=201,
                        branch_id=1,
                        unit_id=1,
                        supplier_id=1,
                        name="Burger Bun",
                        reorder_level="5.00",
                        cost_price="0.30",
                        selling_price="0.90",
                        is_active=True,
                    ),
                    Product(
                        id=202,
                        branch_id=1,
                        unit_id=1,
                        supplier_id=1,
                        name="Beef Patty",
                        reorder_level="5.00",
                        cost_price="0.80",
                        selling_price="2.50",
                        is_active=True,
                    ),
                    Product(
                        id=301,
                        branch_id=2,
                        unit_id=2,
                        supplier_id=2,
                        name="Other Branch Item",
                        reorder_level="1.00",
                        cost_price="0.40",
                        selling_price="1.20",
                        is_active=True,
                    ),
                ]
            )
            await session.commit()

    asyncio.run(_seed())


def test_procurement_order_workflow_receipt_writes_audit_and_stock() -> None:
    session_factory = _build_test_db()
    _seed_procurement_data(session_factory)
    fake_redis = FakeRedis()

    async def _get_redis_override():
        yield fake_redis

    app.dependency_overrides[get_db] = _override_db(session_factory)
    app.dependency_overrides[get_redis] = _get_redis_override

    try:
        client = TestClient(app)
        app.dependency_overrides[get_current_user] = _user_override(user_id=10, role="manager", branch_id=1)
        create_response = client.post(
            "/procurement/orders",
            json={
                "supplier_id": 1,
                "notes": "urgent replenishment",
                "line_items": [
                    {"product_id": 201, "quantity": "5.00", "unit_price": "1.50"},
                    {"product_id": 202, "quantity": "3.00", "unit_price": "2.00"},
                ],
            },
            headers={"x-request-id": "req-week6-create"},
        )
        assert create_response.status_code == 201
        purchase_order_id = create_response.json()["purchase_order_id"]
        line_items = create_response.json()["line_items"]

        submit_response = client.put(
            f"/procurement/orders/{purchase_order_id}/submit",
            headers={"x-request-id": "req-week6-submit"},
        )
        assert submit_response.status_code == 200
        assert submit_response.json()["status"] == "submitted"

        app.dependency_overrides[get_current_user] = _user_override(user_id=20, role="admin", branch_id=1)
        approve_response = client.put(
            f"/procurement/orders/{purchase_order_id}/approve",
            headers={"x-request-id": "req-week6-approve"},
        )
        assert approve_response.status_code == 200
        assert approve_response.json()["status"] == "approved"

        app.dependency_overrides[get_current_user] = _user_override(user_id=10, role="manager", branch_id=1)
        receipt_response = client.post(
            "/procurement/grn",
            json={
                "purchase_order_id": purchase_order_id,
                "reference": "GRN-1001",
                "line_items": [
                    {"purchase_order_line_item_id": line_items[0]["line_item_id"], "quantity_received": "5.00"},
                    {"purchase_order_line_item_id": line_items[1]["line_item_id"], "quantity_received": "3.00"},
                ],
            },
            headers={"x-request-id": "req-week6-grn"},
        )
        assert receipt_response.status_code == 201
        receipt_payload = receipt_response.json()
        assert receipt_payload["status_after_receipt"] == "closed"
        assert len(receipt_payload["line_items"]) == 2

        async def _verify() -> tuple[list[StockMovement], list[str], PurchaseOrder, GoodsReceivedNote | None]:
            async with session_factory() as session:
                movements = (
                    await session.execute(
                        select(StockMovement)
                        .where(StockMovement.branch_id == 1, StockMovement.reference_id == f"grn:{receipt_payload['goods_received_note_id']}")
                        .order_by(StockMovement.id.asc())
                    )
                ).scalars().all()
                actions = (
                    await session.execute(
                        select(AuditLog.action)
                        .where(AuditLog.branch_id == 1)
                        .order_by(AuditLog.id.asc())
                    )
                ).scalars().all()
                po = (
                    await session.execute(select(PurchaseOrder).where(PurchaseOrder.id == purchase_order_id))
                ).scalar_one()
                grn = (
                    await session.execute(select(GoodsReceivedNote).where(GoodsReceivedNote.id == receipt_payload["goods_received_note_id"]))
                ).scalar_one_or_none()
                return list(movements), list(actions), po, grn

        movements, actions, purchase_order, grn = asyncio.run(_verify())
        assert len(movements) == 2
        assert {str(movement.qty) for movement in movements} == {"5.00", "3.00"}
        assert purchase_order.status == "closed"
        assert grn is not None
        assert "purchase_order.create" in actions
        assert "purchase_order.submit" in actions
        assert "purchase_order.approve" in actions
        assert "goods_received_note.create" in actions
        assert actions.count("stock_movement.receive") == 2
        assert fake_redis.deleted_keys == ["inventory:stock:branch:1", "inventory:stock:branch:1"]
    finally:
        app.dependency_overrides.clear()


def test_procurement_rejects_invalid_status_transition_and_branch_access() -> None:
    session_factory = _build_test_db()
    _seed_procurement_data(session_factory)
    fake_redis = FakeRedis()

    async def _get_redis_override():
        yield fake_redis

    app.dependency_overrides[get_db] = _override_db(session_factory)
    app.dependency_overrides[get_redis] = _get_redis_override

    try:
        client = TestClient(app)
        app.dependency_overrides[get_current_user] = _user_override(user_id=10, role="manager", branch_id=1)
        create_response = client.post(
            "/procurement/orders",
            json={
                "supplier_id": 1,
                "line_items": [{"product_id": 201, "quantity": "2.00", "unit_price": "1.20"}],
            },
        )
        assert create_response.status_code == 201
        purchase_order_id = create_response.json()["purchase_order_id"]

        approve_response = client.put(f"/procurement/orders/{purchase_order_id}/approve")
        assert approve_response.status_code == 403

        app.dependency_overrides[get_current_user] = _user_override(user_id=30, role="manager", branch_id=2)
        other_branch_submit = client.put(f"/procurement/orders/{purchase_order_id}/submit")
        assert other_branch_submit.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_procurement_reports_return_order_and_spend_data() -> None:
    session_factory = _build_test_db()
    _seed_procurement_data(session_factory)
    fake_redis = FakeRedis()

    async def _get_redis_override():
        yield fake_redis

    app.dependency_overrides[get_db] = _override_db(session_factory)
    app.dependency_overrides[get_redis] = _get_redis_override

    try:
        client = TestClient(app)
        app.dependency_overrides[get_current_user] = _user_override(user_id=10, role="manager", branch_id=1)
        order = client.post(
            "/procurement/orders",
            json={
                "supplier_id": 1,
                "line_items": [{"product_id": 201, "quantity": "4.00", "unit_price": "1.25"}],
            },
        )
        purchase_order_id = order.json()["purchase_order_id"]
        line_item_id = order.json()["line_items"][0]["line_item_id"]
        client.put(f"/procurement/orders/{purchase_order_id}/submit")

        app.dependency_overrides[get_current_user] = _user_override(user_id=20, role="admin", branch_id=1)
        client.put(f"/procurement/orders/{purchase_order_id}/approve")

        app.dependency_overrides[get_current_user] = _user_override(user_id=10, role="manager", branch_id=1)
        receipt = client.post(
            "/procurement/grn",
            json={
                "purchase_order_id": purchase_order_id,
                "reference": "GRN-REPORT",
                "line_items": [{"purchase_order_line_item_id": line_item_id, "quantity_received": "4.00"}],
            },
        )
        assert receipt.status_code == 201

        orders_report = client.get("/procurement/reports/orders", params={"status": "closed"})
        assert orders_report.status_code == 200
        orders_payload = orders_report.json()
        assert orders_payload["total"] == 1
        assert orders_payload["items"][0]["supplier_name"] == "Acme Foods"
        assert orders_payload["items"][0]["ordered_total"] == "5.00"

        spend_report = client.get("/procurement/reports/spend")
        assert spend_report.status_code == 200
        spend_payload = spend_report.json()
        assert spend_payload["branch_id"] == 1
        assert spend_payload["rows"][0]["supplier_name"] == "Acme Foods"
        assert spend_payload["rows"][0]["total_spend"] == "5.00"
    finally:
        app.dependency_overrides.clear()

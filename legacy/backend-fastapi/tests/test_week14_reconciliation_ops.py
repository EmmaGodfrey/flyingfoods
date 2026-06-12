"""Week 14 tests for reconciliation operations hardening and alert coverage."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.core.celery_app import celery_app
from app.core.observability import reset_metrics, snapshot_metrics
from app.core.redis import get_redis
from app.db.models import BillOfMaterial, Branch, Product, StockMovement, Unit, User
from app.db.session import get_db
from app.main import app
from tests.test_week13_payment_integration import _build_test_db, _override_db

celery_app.conf.task_always_eager = True
celery_app.conf.task_store_eager_result = True
celery_app.conf.result_backend = "cache+memory://"


class FakeRedis:
    async def get(self, _key: str):
        return None

    async def setex(self, _key: str, _ttl: int, _value: str) -> None:
        return None

    async def delete(self, _key: str) -> None:
        return None


async def _get_manager_override() -> User:
    return User(
        id=10,
        email="manager@example.com",
        hashed_password="hashed",
        role="manager",
        branch_id=1,
        is_active=True,
    )


def _seed_pos_sale_data(session_factory) -> None:
    async def _seed() -> None:
        async with session_factory() as session:
            session.add_all(
                [
                    Branch(id=1, code="HQ", name="Headquarters"),
                    Unit(id=1, branch_id=1, name="Piece", symbol="pc"),
                    User(id=10, email="manager@example.com", hashed_password="hashed", role="manager", branch_id=1, is_active=True),
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
                        created_at=datetime(2026, 5, 30, 8, 0, tzinfo=timezone.utc),
                    ),
                    StockMovement(
                        id=2,
                        product_id=201,
                        branch_id=1,
                        qty="20.00",
                        movement_type="receive",
                        reference_id="seed-patty",
                        created_by=10,
                        created_at=datetime(2026, 5, 30, 8, 0, tzinfo=timezone.utc),
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
        headers={"x-request-id": "req-week14-sale"},
    )
    assert response.status_code == 201
    return int(response.json()["sale_id"])


def test_async_reconcile_mismatch_is_labeled_for_alerting() -> None:
    reset_metrics()
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
            headers={"x-request-id": "req-week14-bad-ref"},
        )
        assert enqueue_response.status_code == 202
        job_id = enqueue_response.json()["job_id"]

        for _ in range(30):
            status_response = client.get(f"/sales/{sale_id}/payments/reconcile/jobs/{job_id}")
            assert status_response.status_code == 200
            if status_response.json()["status"] == "failed":
                break
            time.sleep(0.01)

        snapshot = snapshot_metrics()
        matching = [
            point
            for point in snapshot["counters"]
            if point.name == "sales_payment_reconcile_async_failures_total"
            and dict(point.labels).get("reason") == "reference_mismatch"
        ]
        assert matching
        assert matching[0].value >= 1.0
    finally:
        app.dependency_overrides.clear()


def test_week14_alert_rules_include_reconciliation_ops_signals() -> None:
    alerts_path = Path(__file__).resolve().parents[1] / "monitoring" / "prometheus" / "alerts.yml"
    alerts_text = alerts_path.read_text(encoding="utf-8")

    assert "alert: ERPAsyncPaymentReconcileFailures" in alerts_text
    assert "erp_sales_payment_reconcile_async_failures_total" in alerts_text
    assert "alert: ERPAsyncPaymentReconcileQueueLag" in alerts_text
    assert "erp_sales_payment_reconcile_async_enqueued_total" in alerts_text
    assert "erp_sales_payment_reconcile_async_started_total" in alerts_text

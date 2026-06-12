"""Week 7 tests for observability metrics and instrumentation paths."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.core.events import DomainEvent, InProcessEventBus
from app.core.observability import reset_metrics, snapshot_metrics
from app.db.models import AuditLog, User
from app.db.session import get_db
from app.main import app
from tests.test_week6_audit_integration import _build_test_db, _override_db, _seed_identity_data


def _counter_value(metrics: dict[str, list], name: str, **labels: str) -> float:
    target = tuple(sorted((k, str(v)) for k, v in labels.items()))
    for point in metrics["counters"]:
        if point.name == name and point.labels == target:
            return point.value
    return 0.0


def _has_histogram(metrics: dict[str, list], name: str, **labels: str) -> bool:
    target = tuple(sorted((k, str(v)) for k, v in labels.items()))
    return any(point.name == name and point.labels == target for point in metrics["histograms"])


def test_event_bus_records_publish_and_failure_metrics() -> None:
    reset_metrics()
    bus = InProcessEventBus()

    async def success_handler(_event: DomainEvent, _context: dict[str, object]) -> None:
        return None

    async def failing_handler(_event: DomainEvent, _context: dict[str, object]) -> None:
        raise RuntimeError("forced failure")

    bus.subscribe("inventory.write.v1", success_handler)
    bus.subscribe("inventory.write.v1", failing_handler)

    event = DomainEvent(
        type="inventory.write.v1",
        branch_id=1,
        correlation_id="req-week7-ev-001",
        payload={"action": "product.create"},
    )
    asyncio.run(bus.publish(event, {}))

    metrics = snapshot_metrics()
    assert _counter_value(metrics, "event_publish_total", event_type="inventory.write.v1", branch_id="1") == 1.0
    assert _counter_value(
        metrics,
        "event_handler_success_total",
        event_type="inventory.write.v1",
        handler="success_handler",
    ) == 1.0
    assert _counter_value(
        metrics,
        "event_handler_failures_total",
        event_type="inventory.write.v1",
        handler="failing_handler",
    ) == 1.0
    assert _has_histogram(metrics, "event_publish_duration_ms", event_type="inventory.write.v1", branch_id="1")


def test_audit_query_records_throughput_latency_and_denials() -> None:
    reset_metrics()
    session_factory = _build_test_db()
    _seed_identity_data(session_factory)

    async def _seed_logs() -> None:
        async with session_factory() as session:
            session.add(
                AuditLog(
                    occurred_at=datetime(2026, 5, 28, 12, 0, tzinfo=timezone.utc),
                    actor_user_id=11,
                    branch_id=1,
                    action="product.create",
                    entity_type="product",
                    entity_id="200",
                    before_json=None,
                    after_json={"id": 200},
                    request_id="req-week7-audit-001",
                    source="api",
                    schema_version=1,
                    hash_chain_prev=None,
                    hash_chain_curr="d" * 64,
                )
            )
            await session.commit()

    asyncio.run(_seed_logs())

    async def _get_admin_override() -> User:
        return User(
            id=11,
            email="admin@example.com",
            hashed_password="hashed",
            role="admin",
            branch_id=1,
            is_active=True,
        )

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

    try:
        client = TestClient(app)

        app.dependency_overrides[get_current_user] = _get_admin_override
        success_response = client.get("/audit/logs", params={"branch_id": 1}, headers={"x-request-id": "req-week7-s-001"})
        assert success_response.status_code == 200

        app.dependency_overrides[get_current_user] = _get_manager_override
        denied_response = client.get("/audit/logs", params={"branch_id": 2}, headers={"x-request-id": "req-week7-d-001"})
        assert denied_response.status_code == 403

        metrics = snapshot_metrics()
        assert _counter_value(metrics, "audit_query_requests_total", role="admin") == 1.0
        assert _counter_value(metrics, "audit_query_requests_total", role="manager") == 1.0
        assert _counter_value(metrics, "audit_query_denied_total", role="manager") == 1.0
        assert _has_histogram(metrics, "audit_query_latency_ms", role="admin")
    finally:
        app.dependency_overrides.clear()

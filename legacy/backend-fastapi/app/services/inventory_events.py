"""Inventory event handlers for audit logging and cache invalidation."""

from __future__ import annotations

from typing import Any

from app.core.events import DomainEvent, get_event_bus
from app.core.websockets import get_dashboard_ws_manager
from app.services.audit_service import INVENTORY_WRITE_EVENT, write_audit_log_from_event
from app.services.inventory_service import invalidate_stock_cache


def register_inventory_event_handlers() -> None:
    event_bus = get_event_bus()
    event_bus.subscribe(INVENTORY_WRITE_EVENT, write_audit_log_from_event)
    event_bus.subscribe(INVENTORY_WRITE_EVENT, invalidate_stock_cache_from_event)
    event_bus.subscribe(INVENTORY_WRITE_EVENT, broadcast_dashboard_event_from_domain_write)


async def invalidate_stock_cache_from_event(event: DomainEvent, context: dict[str, Any]) -> None:
    redis_client = context.get("redis_client")
    await invalidate_stock_cache(redis_client, branch_id=event.branch_id)


async def broadcast_dashboard_event_from_domain_write(event: DomainEvent, context: dict[str, Any]) -> None:
    _ = context
    payload = event.payload
    action = str(payload.get("action", "unknown"))

    manager = get_dashboard_ws_manager()
    await manager.broadcast_to_branch(
        event.branch_id,
        {
            "type": "domain_event",
            "event_type": event.type,
            "action": action,
            "entity_type": payload.get("entity_type"),
            "entity_id": payload.get("entity_id"),
            "occurred_at": event.occurred_at.isoformat(),
            "correlation_id": event.correlation_id,
        },
    )

    if action in {"sale.void", "sale.refund"}:
        await manager.broadcast_to_branch(
            event.branch_id,
            {
                "type": "anomaly_alert",
                "level": "warning",
                "message": f"Alert: unusual {action} activity detected",
                "occurred_at": event.occurred_at.isoformat(),
                "correlation_id": event.correlation_id,
            },
        )

"""Unit tests for week 5 audit and event bus behavior."""

from app.core.events import DomainEvent, InProcessEventBus
from app.services.audit_service import compute_hash_chain, resolve_audit_branch_scope


def test_compute_hash_chain_changes_with_payload() -> None:
    first = compute_hash_chain(None, {"action": "product.create", "entity_id": "1"})
    second = compute_hash_chain(None, {"action": "product.create", "entity_id": "2"})

    assert first != second
    assert len(first) == 64


def test_resolve_branch_scope_denies_non_elevated_cross_branch() -> None:
    try:
        resolve_audit_branch_scope(requested_branch_id=2, current_user_role="manager", current_user_branch_id=1)
        assert False, "Expected PermissionError for cross-branch access"
    except PermissionError:
        assert True


def test_event_bus_isolates_handler_failures_and_is_idempotent() -> None:
    bus = InProcessEventBus()
    calls: list[str] = []

    async def bad_handler(_event: DomainEvent, _context: dict[str, object]) -> None:
        calls.append("bad")
        raise RuntimeError("boom")

    async def good_handler(_event: DomainEvent, _context: dict[str, object]) -> None:
        calls.append("good")

    bus.subscribe("inventory.write.v1", bad_handler)
    bus.subscribe("inventory.write.v1", good_handler)

    event = DomainEvent(type="inventory.write.v1", branch_id=1, payload={"action": "product.create"})

    import asyncio

    asyncio.run(bus.publish(event, {}))
    asyncio.run(bus.publish(event, {}))

    assert calls.count("bad") == 1
    assert calls.count("good") == 1

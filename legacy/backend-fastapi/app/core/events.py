"""In-process event bus for domain events."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from time import perf_counter
from typing import Any
from uuid import uuid4

from app.core.observability import increment_counter, log_event, measure_elapsed_ms, observe_histogram_ms

EventHandler = Callable[["DomainEvent", dict[str, Any]], Awaitable[None]]


@dataclass(slots=True)
class DomainEvent:
    """Generic event envelope for domain writes."""

    type: str
    branch_id: int
    payload: dict[str, Any]
    correlation_id: str | None = None
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    id: str = field(default_factory=lambda: str(uuid4()))


class InProcessEventBus:
    """Simple async pub/sub bus with per-process idempotency."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._processed_event_ids: set[str] = set()

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        handlers = self._handlers[event_type]
        if handler in handlers:
            return
        handlers.append(handler)

    async def publish(self, event: DomainEvent, context: dict[str, Any] | None = None) -> None:
        if event.id in self._processed_event_ids:
            increment_counter("event_publish_duplicates_total", event_type=event.type)
            log_event(
                "event.publish.duplicate",
                event_id=event.id,
                event_type=event.type,
                correlation_id=event.correlation_id,
                branch_id=event.branch_id,
            )
            return

        self._processed_event_ids.add(event.id)
        increment_counter("event_publish_total", event_type=event.type, branch_id=event.branch_id)
        handlers = self._handlers.get(event.type, [])
        if not handlers:
            log_event(
                "event.publish.no_handlers",
                event_id=event.id,
                event_type=event.type,
                correlation_id=event.correlation_id,
                branch_id=event.branch_id,
            )
            return

        event_context = context or {}
        publish_started = perf_counter()
        for handler in handlers:
            handler_name = getattr(handler, "__name__", repr(handler))
            started = perf_counter()
            try:
                await handler(event, event_context)
                duration_ms = measure_elapsed_ms(started)
                increment_counter(
                    "event_handler_success_total",
                    event_type=event.type,
                    handler=handler_name,
                )
                observe_histogram_ms(
                    "event_handler_duration_ms",
                    duration_ms,
                    event_type=event.type,
                    handler=handler_name,
                )
                log_event(
                    "event.handler.success",
                    event_id=event.id,
                    event_type=event.type,
                    handler=handler_name,
                    duration_ms=f"{duration_ms:.2f}",
                    correlation_id=event.correlation_id,
                    branch_id=event.branch_id,
                )
            except Exception:  # noqa: BLE001
                duration_ms = measure_elapsed_ms(started)
                increment_counter(
                    "event_handler_failures_total",
                    event_type=event.type,
                    handler=handler_name,
                )
                observe_histogram_ms(
                    "event_handler_duration_ms",
                    duration_ms,
                    event_type=event.type,
                    handler=handler_name,
                )
                log_event(
                    "event.handler.failure",
                    level="exception",
                    event_id=event.id,
                    event_type=event.type,
                    handler=handler_name,
                    duration_ms=f"{duration_ms:.2f}",
                    correlation_id=event.correlation_id,
                    branch_id=event.branch_id,
                )

        total_duration_ms = measure_elapsed_ms(publish_started)
        observe_histogram_ms("event_publish_duration_ms", total_duration_ms, event_type=event.type, branch_id=event.branch_id)
        log_event(
            "event.publish.complete",
            event_id=event.id,
            event_type=event.type,
            duration_ms=f"{total_duration_ms:.2f}",
            correlation_id=event.correlation_id,
            branch_id=event.branch_id,
        )


_event_bus: InProcessEventBus | None = None


def get_event_bus() -> InProcessEventBus:
    global _event_bus
    if _event_bus is None:
        _event_bus = InProcessEventBus()
    return _event_bus

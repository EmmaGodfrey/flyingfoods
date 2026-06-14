"""Channels broadcast helpers for kitchen and waiter groups.

Sockets are notification-only: the server pushes a small event and clients
refetch through their REST/React-Query layer. REST stays the source of truth.
"""

from typing import Any

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

KITCHEN_GROUP = "kitchen"
WAITER_GROUP = "waiter"


def broadcast_order_event(event_type: str, order_id: Any) -> None:
    """Notify both kitchen and waiter groups that an order changed.

    Safe to call when no channel layer is configured (e.g. during tests):
    the broadcast is silently skipped.
    """
    layer = get_channel_layer()
    if layer is None:
        return
    message = {"type": "order.event", "event": event_type, "order_id": str(order_id)}
    for group in (KITCHEN_GROUP, WAITER_GROUP):
        async_to_sync(layer.group_send)(group, message)

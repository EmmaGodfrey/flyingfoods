"""WebSocket consumers for the kitchen display and waiter view."""

from typing import Any

from channels.generic.websocket import AsyncJsonWebsocketConsumer

from apps.kitchen.realtime import KITCHEN_GROUP, WAITER_GROUP
from apps.users.models import User

_GROUP_ROLES = {
    KITCHEN_GROUP: (User.Role.CHEF, User.Role.STOREKEEPER, User.Role.MANAGER, User.Role.ADMIN),
    WAITER_GROUP: (User.Role.WAITER, User.Role.MANAGER, User.Role.ADMIN),
}


class _OrderConsumer(AsyncJsonWebsocketConsumer):
    """Base consumer: role-gated join, forwards order events to the client."""

    group_name: str = ""

    async def connect(self) -> None:
        """Accept only authenticated users holding an allowed role."""
        user = self.scope.get("user")
        if not user or not user.is_authenticated or user.role not in _GROUP_ROLES[self.group_name]:
            await self.close(code=4403)
            return
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code: int) -> None:
        """Leave the group on disconnect."""
        if self.group_name:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def order_event(self, event: dict[str, Any]) -> None:
        """Forward an order.* event to the connected client."""
        await self.send_json({"event": event["event"], "order_id": event["order_id"]})


class KitchenConsumer(_OrderConsumer):
    """Kitchen display socket."""

    group_name = KITCHEN_GROUP


class WaiterConsumer(_OrderConsumer):
    """Waiter view socket."""

    group_name = WAITER_GROUP

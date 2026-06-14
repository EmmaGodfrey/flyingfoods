"""WebSocket URL routing for kitchen and waiter consumers."""

from django.urls import path

from apps.kitchen.consumers import KitchenConsumer, WaiterConsumer

websocket_urlpatterns = [
    path("ws/kitchen/", KitchenConsumer.as_asgi()),
    path("ws/waiter/", WaiterConsumer.as_asgi()),
]

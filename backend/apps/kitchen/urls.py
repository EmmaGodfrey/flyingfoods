"""Kitchen and waiter URL routes, mounted under /api/ by config/urls.py."""

from django.urls import path

from apps.kitchen.views import (
    ExtraUsageView,
    KitchenOrderListView,
    OutOfStockClearView,
    OutOfStockListCreateView,
    ReadyOrderView,
    ReturnOrderView,
    ServeOrderView,
    StartOrderView,
    WaiterOrderListView,
)

urlpatterns = [
    path("kitchen/orders/", KitchenOrderListView.as_view(), name="kitchen-orders"),
    path("kitchen/orders/<uuid:pk>/start/", StartOrderView.as_view(), name="kitchen-start"),
    path("kitchen/orders/<uuid:pk>/ready/", ReadyOrderView.as_view(), name="kitchen-ready"),
    path("kitchen/orders/<uuid:pk>/extra-usage/", ExtraUsageView.as_view(), name="kitchen-extra-usage"),
    path("kitchen/out-of-stock/", OutOfStockListCreateView.as_view(), name="kitchen-oos"),
    path("kitchen/out-of-stock/<uuid:pk>/", OutOfStockClearView.as_view(), name="kitchen-oos-clear"),
    path("waiter/orders/", WaiterOrderListView.as_view(), name="waiter-orders"),
    path("waiter/orders/<uuid:pk>/served/", ServeOrderView.as_view(), name="waiter-served"),
    path("waiter/orders/<uuid:pk>/return/", ReturnOrderView.as_view(), name="waiter-return"),
]

"""Tests for the order lifecycle and waiter actions via the API."""

import datetime
from decimal import Decimal

import pytest

from apps.inventory.services import MovementLine, post_movements
from apps.kitchen.models import Order
from apps.menu.models import MenuItem
from apps.menu.services import create_recipe_version, publish_version
from apps.pos_ingest.services import ingest_sale_event

pytestmark = pytest.mark.django_db


@pytest.fixture
def order(product, locations):
    """An ingested order ready to walk through the lifecycle."""
    post_movements(
        document_type="Opening",
        document_id=product.pk,
        lines=[
            MovementLine(
                product_id=product.pk,
                location_id=locations["stores"].pk,
                qty_delta=Decimal("100"),
                movement_type="GRN_RECEIPT",
            )
        ],
    )
    item = MenuItem.objects.create(name="Burger", pos_code="BURGER")
    version = create_recipe_version(menu_item=item, lines=[(product.pk, Decimal("1"))])
    publish_version(version=version, effective_from=datetime.date(2020, 1, 1))
    ingest_sale_event(
        {
            "pos_sale_id": "POS-LC",
            "sold_at": "2026-06-12T10:00:00Z",
            "lines": [{"pos_code": "BURGER", "qty": 1}],
        }
    )
    return Order.objects.get()


def test_full_lifecycle_to_served(auth_client, order):
    """Chef starts and readies; waiter serves; statuses and events recorded."""
    chef = auth_client("CHEF")
    assert chef.post(f"/api/kitchen/orders/{order.pk}/start/").status_code == 200
    assert chef.post(f"/api/kitchen/orders/{order.pk}/ready/").status_code == 200

    waiter = auth_client("WAITER")
    resp = waiter.post(f"/api/waiter/orders/{order.pk}/served/")
    assert resp.status_code == 200

    order.refresh_from_db()
    assert order.status == Order.Status.SERVED
    assert order.status_events.filter(status="SERVED").exists()


def test_double_serve_conflicts(auth_client, order):
    """A second serve on the same order returns 409 ALREADY_SERVED."""
    order.status = Order.Status.READY
    order.save()
    waiter = auth_client("WAITER")
    assert waiter.post(f"/api/waiter/orders/{order.pk}/served/").status_code == 200
    resp = waiter.post(f"/api/waiter/orders/{order.pk}/served/")
    assert resp.status_code == 409
    assert resp.data["error"]["code"] == "ALREADY_SERVED"


def test_waiter_cannot_start_order(auth_client, order):
    """A waiter hitting a chef-only endpoint is forbidden."""
    waiter = auth_client("WAITER")
    assert waiter.post(f"/api/kitchen/orders/{order.pk}/start/").status_code == 403


def test_unauthenticated_rejected(api_client, order):
    """Anonymous access to the kitchen list is rejected."""
    assert api_client.get("/api/kitchen/orders/").status_code == 401

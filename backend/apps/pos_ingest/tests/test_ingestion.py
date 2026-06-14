"""Tests for POS ingestion: dedupe, deduction, and unknown-item flagging."""

import datetime
from decimal import Decimal

import pytest

from apps.inventory.models import StockMovement
from apps.inventory.services import MovementLine, on_hand, post_movements
from apps.kitchen.models import Order
from apps.menu.models import MenuItem
from apps.menu.services import create_recipe_version, publish_version
from apps.pos_ingest.models import SaleEvent
from apps.pos_ingest.services import ingest_sale_event

pytestmark = pytest.mark.django_db


@pytest.fixture
def burger(product, locations):
    """A published Beef Burger recipe needing 2 units of `product`, with stock."""
    post_movements(
        document_type="Opening",
        document_id=product.pk,
        lines=[
            MovementLine(
                product_id=product.pk,
                location_id=locations["stores"].pk,
                qty_delta=Decimal("100"),
                movement_type="GRN_RECEIPT",
                unit_cost=Decimal("2.00"),
            )
        ],
    )
    item = MenuItem.objects.create(name="Beef Burger", pos_code="BURGER")
    version = create_recipe_version(menu_item=item, lines=[(product.pk, Decimal("2"))])
    publish_version(version=version, effective_from=datetime.date(2020, 1, 1))
    return item


def _payload(sale_id="POS-1"):
    return {
        "pos_sale_id": sale_id,
        "sold_at": "2026-06-12T10:00:00Z",
        "cashier": "till-1",
        "lines": [{"pos_code": "BURGER", "qty": 3}],
        "totals": {"gross": "36.00"},
    }


def test_ingestion_creates_order_and_deducts_stock(burger, product, locations):
    """A sale creates an order and deducts the recipe quantity from Stores."""
    ingest_sale_event(_payload())

    assert Order.objects.count() == 1
    # 3 burgers x 2 units = 6 deducted from 100.
    assert on_hand(product.pk, locations["stores"].pk) == Decimal("94")


def test_duplicate_sale_id_ingested_once(burger):
    """The same POS sale ID never produces two orders."""
    ingest_sale_event(_payload("POS-DUP"))
    ingest_sale_event(_payload("POS-DUP"))

    assert SaleEvent.objects.filter(pos_sale_id="POS-DUP").count() == 1
    assert Order.objects.count() == 1


def test_unknown_item_flags_event_without_deduction(product, locations):
    """A sale for an item with no published recipe is flagged, no deduction."""
    event = ingest_sale_event(_payload("POS-UNK"))

    assert event.status == SaleEvent.Status.FLAGGED_UNKNOWN_ITEM
    assert not StockMovement.objects.filter(document_type="Order").exists()


def test_raw_payload_is_persisted(burger):
    """The raw POS payload is retained verbatim for audit."""
    event = ingest_sale_event(_payload("POS-RAW"))
    assert event.payload["pos_sale_id"] == "POS-RAW"
    assert event.payload["totals"]["gross"] == "36.00"

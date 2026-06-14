"""Tests for recipe versioning: history correctness and immutability (SC-010)."""

import datetime
from decimal import Decimal

import pytest

from apps.core.exceptions import HasHistoryError, ImmutableVersionError
from apps.inventory.services import MovementLine, post_movements
from apps.kitchen.models import OrderItem
from apps.menu.models import MenuItem, RecipeVersion
from apps.menu.services import create_recipe_version, guard_delete, publish_version
from apps.pos_ingest.services import ingest_sale_event

pytestmark = pytest.mark.django_db


@pytest.fixture
def stocked_product(product, locations):
    """A product with ample stock at Restaurant Stores."""
    post_movements(
        document_type="Opening",
        document_id=product.pk,
        lines=[
            MovementLine(
                product_id=product.pk,
                location_id=locations["stores"].pk,
                qty_delta=Decimal("1000"),
                movement_type="GRN_RECEIPT",
                unit_cost=Decimal("2.00"),
            )
        ],
    )
    return product


def _sale(sale_id, qty=1):
    return {
        "pos_sale_id": sale_id,
        "sold_at": "2026-06-12T10:00:00Z",
        "lines": [{"pos_code": "BURGER", "qty": qty}],
    }


def test_historical_order_keeps_its_recipe_version(stocked_product, locations):
    """An order placed under v1 still references v1 after v2 publishes (SC-010)."""
    item = MenuItem.objects.create(name="Burger", pos_code="BURGER")
    v1 = create_recipe_version(menu_item=item, lines=[(stocked_product.pk, Decimal("2"))])
    publish_version(version=v1, effective_from=datetime.date(2020, 1, 1))

    ingest_sale_event(_sale("S1"))
    first_item = OrderItem.objects.get()
    assert first_item.recipe_version_id == v1.pk

    # Publish a v2 with a different quantity, effective today.
    v2 = create_recipe_version(menu_item=item, lines=[(stocked_product.pk, Decimal("5"))])
    publish_version(version=v2, effective_from=datetime.date.today())

    # The original order still points at v1; its snapshot is unchanged.
    first_item.refresh_from_db()
    assert first_item.recipe_version_id == v1.pk
    assert v1.lines.get().qty_per_serving == Decimal("2")


def test_published_version_is_immutable(stocked_product):
    """Editing a published version is refused."""
    item = MenuItem.objects.create(name="Burger", pos_code="BURGER")
    v1 = create_recipe_version(menu_item=item, lines=[(stocked_product.pk, Decimal("2"))])
    publish_version(version=v1, effective_from=datetime.date(2020, 1, 1))

    v1.selling_price_snapshot = Decimal("99")
    with pytest.raises(ImmutableVersionError):
        v1.save()


def test_publish_retires_previous_version(stocked_product):
    """Publishing v2 retires v1 and closes its effective window."""
    item = MenuItem.objects.create(name="Burger", pos_code="BURGER")
    v1 = create_recipe_version(menu_item=item, lines=[(stocked_product.pk, Decimal("2"))])
    publish_version(version=v1, effective_from=datetime.date(2020, 1, 1))
    v2 = create_recipe_version(menu_item=item, lines=[(stocked_product.pk, Decimal("3"))])
    publish_version(version=v2, effective_from=datetime.date(2026, 1, 1))

    v1.refresh_from_db()
    assert v1.status == RecipeVersion.Status.RETIRED
    assert v1.effective_to == datetime.date(2026, 1, 1)


def test_delete_guarded_when_history_exists(stocked_product, locations):
    """A menu item with order history cannot be hard-deleted."""
    item = MenuItem.objects.create(name="Burger", pos_code="BURGER")
    v1 = create_recipe_version(menu_item=item, lines=[(stocked_product.pk, Decimal("1"))])
    publish_version(version=v1, effective_from=datetime.date(2020, 1, 1))
    ingest_sale_event(_sale("S2"))

    with pytest.raises(HasHistoryError):
        guard_delete(menu_item=item)

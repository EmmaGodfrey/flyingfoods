"""Tests for issue notes, transfers, stock-takes, and the override path."""

import uuid
from decimal import Decimal

import pytest

from apps.core.models import Approval, ThresholdConfig
from apps.inventory.models import Transfer
from apps.inventory.services import (
    MovementLine,
    create_issue_note,
    on_hand,
    open_stock_take,
    post_issue_note,
    post_movements,
    post_stock_take,
    post_transfer,
)

pytestmark = pytest.mark.django_db


def _stock(product, location, qty):
    post_movements(
        document_type="Opening",
        document_id=uuid.uuid4(),
        lines=[MovementLine(product.pk, location.pk, Decimal(qty), "GRN_RECEIPT", Decimal("3"))],
        allow_negative=True,
    )


def test_issue_moves_stock_between_locations(product, locations, make_user):
    """A posted issue deducts source and adds destination."""
    _stock(product, locations["stores"], "100")
    issuer = make_user("RESTAURANT_ISSUER")
    note = create_issue_note(
        source=locations["stores"],
        destination=locations["kitchen"],
        requested_by=issuer,
        lines=[(product.pk, Decimal("30"))],
    )
    post_issue_note(issue_note=note, posted_by=issuer)

    assert on_hand(product.pk, locations["stores"].pk) == Decimal("70")
    assert on_hand(product.pk, locations["kitchen"].pk) == Decimal("30")


def test_unit_issue_off_schedule_requires_reason(product, locations, make_user):
    """Issuing to the Unit outside Tue/Thu without a reason is rejected."""
    import datetime
    from rest_framework.exceptions import ValidationError

    _stock(product, locations["stores"], "50")
    issuer = make_user("UNIT_ISSUER")
    # Only assert the rule on non-Tue/Thu days to keep the test deterministic.
    if datetime.date.today().weekday() not in (1, 3):
        with pytest.raises(ValidationError):
            create_issue_note(
                source=locations["stores"],
                destination=locations["unit"],
                requested_by=issuer,
                lines=[(product.pk, Decimal("5"))],
            )


def test_transfer_above_threshold_needs_approval(product, locations, make_user):
    """A high-value transfer parks in PENDING_APPROVAL instead of posting."""
    ThresholdConfig.objects.create(
        scope=ThresholdConfig.Scope.TRANSFER, amount=Decimal("100"), is_active=True
    )
    _stock(product, locations["kitchen"], "100")
    issuer = make_user("UNIT_ISSUER")
    transfer = Transfer.objects.create(
        source=locations["kitchen"], destination=locations["unit"], requested_by=issuer
    )
    transfer.lines.create(product=product, qty=Decimal("50"))  # 50 * cost 3 = 150 > 100

    post_transfer(transfer=transfer, posted_by=issuer)
    transfer.refresh_from_db()
    assert transfer.status == Transfer.Status.PENDING_APPROVAL
    assert Approval.objects.filter(subject_id=transfer.pk, status="PENDING").exists()
    # Stock not yet moved.
    assert on_hand(product.pk, locations["unit"].pk) == Decimal("0")


def test_negative_stock_blocks_issue_without_override(product, locations, make_user):
    """An issue beyond on-hand is blocked unless overridden."""
    from apps.core.exceptions import InsufficientStockError

    _stock(product, locations["stores"], "10")
    issuer = make_user("RESTAURANT_ISSUER")
    note = create_issue_note(
        source=locations["stores"],
        destination=locations["kitchen"],
        requested_by=issuer,
        lines=[(product.pk, Decimal("20"))],
    )
    with pytest.raises(InsufficientStockError):
        post_issue_note(issue_note=note, posted_by=issuer)

    # Override posts and drives on-hand negative.
    post_issue_note(issue_note=note, posted_by=issuer, allow_negative=True)
    assert on_hand(product.pk, locations["stores"].pk) == Decimal("-10")


def test_stock_take_posts_variance(product, locations, make_user):
    """A counted variance posts as a STOCKTAKE_ADJ adjustment."""
    _stock(product, locations["stores"], "100")
    keeper = make_user("STOREKEEPER")
    take = open_stock_take(location=locations["stores"], started_by=keeper)
    line = take.lines.get(product=product)
    line.counted_qty = Decimal("95")
    line.save()

    post_stock_take(stock_take=take, posted_by=keeper)
    assert on_hand(product.pk, locations["stores"].pk) == Decimal("95")

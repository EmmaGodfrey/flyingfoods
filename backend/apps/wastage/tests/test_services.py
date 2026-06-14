"""Tests for wastage logging, threshold routing, and stock posting."""

from decimal import Decimal

import pytest

from apps.core.models import Approval, ReasonCode, ThresholdConfig
from apps.inventory.services import MovementLine, on_hand, post_movements
from apps.wastage.models import WastageEntry
from apps.wastage.services import create_wastage

pytestmark = pytest.mark.django_db


@pytest.fixture
def reason(db):
    """A wastage reason code."""
    return ReasonCode.objects.create(category=ReasonCode.Category.WASTAGE, label="Spoiled")


def _stock(product, location, qty, cost="4"):
    post_movements(
        document_type="Opening",
        document_id=product.pk,
        lines=[MovementLine(product.pk, location.pk, Decimal(qty), "GRN_RECEIPT", Decimal(cost))],
        allow_negative=True,
    )


def test_below_threshold_posts_immediately(product, locations, reason, make_user):
    """A small wastage value posts straight away and deducts stock."""
    ThresholdConfig.objects.create(
        scope=ThresholdConfig.Scope.WASTAGE, amount=Decimal("100"), is_active=True
    )
    _stock(product, locations["stores"], "50")
    keeper = make_user("STOREKEEPER")
    entry = create_wastage(
        entry_type=WastageEntry.EntryType.SPOILAGE,
        product_id=product.pk,
        location_id=locations["stores"].pk,
        qty=Decimal("5"),  # 5 * 4 = 20 < 100
        reason_code=reason,
        logged_by=keeper,
    )
    assert entry.status == WastageEntry.Status.POSTED
    assert on_hand(product.pk, locations["stores"].pk) == Decimal("45")


def test_above_threshold_awaits_approval(product, locations, reason, make_user):
    """A large wastage value parks for Manager approval and does not deduct."""
    ThresholdConfig.objects.create(
        scope=ThresholdConfig.Scope.WASTAGE, amount=Decimal("100"), is_active=True
    )
    _stock(product, locations["stores"], "50")
    keeper = make_user("STOREKEEPER")
    entry = create_wastage(
        entry_type=WastageEntry.EntryType.BREAKAGE,
        product_id=product.pk,
        location_id=locations["stores"].pk,
        qty=Decimal("40"),  # 40 * 4 = 160 > 100
        reason_code=reason,
        logged_by=keeper,
    )
    assert entry.status == WastageEntry.Status.PENDING_APPROVAL
    assert on_hand(product.pk, locations["stores"].pk) == Decimal("50")
    assert Approval.objects.filter(subject_id=entry.pk, status="PENDING").exists()


def test_approval_posts_the_wastage(product, locations, reason, make_user):
    """Approving a pending wastage entry deducts the stock."""
    from apps.core.services import decide_approval

    ThresholdConfig.objects.create(
        scope=ThresholdConfig.Scope.WASTAGE, amount=Decimal("100"), is_active=True
    )
    _stock(product, locations["stores"], "50")
    keeper = make_user("STOREKEEPER")
    manager = make_user("MANAGER")
    entry = create_wastage(
        entry_type=WastageEntry.EntryType.BREAKAGE,
        product_id=product.pk,
        location_id=locations["stores"].pk,
        qty=Decimal("40"),
        reason_code=reason,
        logged_by=keeper,
    )
    approval = Approval.objects.get(subject_id=entry.pk)
    decide_approval(approval=approval, decided_by=manager, decision=Approval.Status.APPROVED)

    entry.refresh_from_db()
    assert entry.status == WastageEntry.Status.POSTED
    assert on_hand(product.pk, locations["stores"].pk) == Decimal("10")

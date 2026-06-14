"""Tests for the generic approval engine and threshold routing."""

from decimal import Decimal

import pytest

from apps.core.models import Approval, ThresholdConfig
from apps.core.services import (
    decide_approval,
    requires_approval,
    submit_for_approval,
)
from apps.masterdata.models import Category, Product

pytestmark = pytest.mark.django_db


@pytest.fixture
def threshold(db):
    """An active transfer threshold of 500."""
    return ThresholdConfig.objects.create(
        scope=ThresholdConfig.Scope.TRANSFER, amount=Decimal("500"), is_active=True
    )


@pytest.fixture
def subject(db):
    """Any model instance to hang an approval on."""
    category = Category.objects.create(name="C")
    return Product.objects.create(
        code="X", name="X", category=category, stock_uom="ea", purchase_uom="ea", recipe_uom="ea"
    )


def test_requires_approval_compares_to_threshold(threshold):
    """Values above the threshold need approval; at/below do not."""
    assert requires_approval(ThresholdConfig.Scope.TRANSFER, Decimal("501")) is True
    assert requires_approval(ThresholdConfig.Scope.TRANSFER, Decimal("500")) is False


def test_threshold_snapshot_taken_at_submission(threshold, subject, make_user):
    """The threshold in force is recorded on the approval at submission time."""
    manager = make_user("MANAGER")
    approval = submit_for_approval(
        subject=subject,
        scope=ThresholdConfig.Scope.TRANSFER,
        requested_by=manager,
        value=Decimal("600"),
    )
    assert approval.threshold_snapshot == Decimal("500")

    threshold.amount = Decimal("9999")
    threshold.save()
    approval.refresh_from_db()
    assert approval.threshold_snapshot == Decimal("500")


def test_reject_requires_reason(subject, make_user):
    """Rejecting without a reason is a validation error."""
    from rest_framework.exceptions import ValidationError

    manager = make_user("MANAGER")
    approval = submit_for_approval(
        subject=subject, scope=ThresholdConfig.Scope.WASTAGE, requested_by=manager
    )
    with pytest.raises(ValidationError):
        decide_approval(approval=approval, decided_by=manager, decision=Approval.Status.REJECTED)


def test_decision_is_final(subject, make_user):
    """A finalised approval cannot be decided again."""
    from rest_framework.exceptions import ValidationError

    manager = make_user("MANAGER")
    approval = submit_for_approval(
        subject=subject, scope=ThresholdConfig.Scope.WASTAGE, requested_by=manager
    )
    decide_approval(approval=approval, decided_by=manager, decision=Approval.Status.APPROVED)
    with pytest.raises(ValidationError):
        decide_approval(approval=approval, decided_by=manager, decision=Approval.Status.APPROVED)

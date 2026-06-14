"""Tests for the stock-ledger choke point: invariants and guards."""

from decimal import Decimal

import pytest

from apps.core.exceptions import InsufficientStockError
from apps.core.models import OutboxRecord
from apps.inventory.models import StockMovement
from apps.inventory.services import MovementLine, on_hand, post_movements

pytestmark = pytest.mark.django_db


def _line(product, location, qty, mtype="GRN_RECEIPT"):
    return MovementLine(product_id=product.pk, location_id=location.pk, qty_delta=qty, movement_type=mtype)


def test_post_movements_updates_balance_and_writes_outbox(product, locations):
    """A posted movement updates on-hand and creates exactly one outbox record."""
    post_movements(
        document_type="GRN",
        document_id=product.pk,
        lines=[_line(product, locations["stores"], Decimal("50"))],
    )

    assert on_hand(product.pk, locations["stores"].pk) == Decimal("50")
    assert OutboxRecord.objects.count() == 1
    assert StockMovement.objects.count() == 1


def test_negative_stock_is_blocked_without_override(product, locations):
    """A deduction below zero raises InsufficientStockError."""
    with pytest.raises(InsufficientStockError):
        post_movements(
            document_type="Issue",
            document_id=product.pk,
            lines=[_line(product, locations["stores"], Decimal("-5"), "ISSUE_OUT")],
        )


def test_negative_stock_allowed_with_override(product, locations):
    """allow_negative lets stock go below zero (Manager override path)."""
    post_movements(
        document_type="Override",
        document_id=product.pk,
        lines=[_line(product, locations["stores"], Decimal("-5"), "OVERRIDE_ADJ")],
        allow_negative=True,
    )
    assert on_hand(product.pk, locations["stores"].pk) == Decimal("-5")


def test_posting_is_idempotent_per_document(product, locations):
    """Posting the same document twice does not double-apply."""
    doc_id = product.pk
    post_movements(
        document_type="GRN",
        document_id=doc_id,
        lines=[_line(product, locations["stores"], Decimal("10"))],
    )
    post_movements(
        document_type="GRN",
        document_id=doc_id,
        lines=[_line(product, locations["stores"], Decimal("10"))],
    )
    assert on_hand(product.pk, locations["stores"].pk) == Decimal("10")
    assert StockMovement.objects.filter(document_id=doc_id).count() == 1


def test_ledger_is_append_only(product, locations):
    """StockMovement rows reject update and delete."""
    post_movements(
        document_type="GRN",
        document_id=product.pk,
        lines=[_line(product, locations["stores"], Decimal("10"))],
    )
    movement = StockMovement.objects.first()
    with pytest.raises(RuntimeError):
        movement.qty_delta = Decimal("999")
        movement.save()
    with pytest.raises(RuntimeError):
        StockMovement.objects.all().delete()

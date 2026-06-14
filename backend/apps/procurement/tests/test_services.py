"""Service-layer tests for the procurement module."""

from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.core.models import Approval
from apps.masterdata.models import Category, Location, Product, Supplier
from apps.notifications.models import Notification
from apps.procurement.models import (
    GRN,
    BudgetLine,
    GRNLine,
    InvoiceMatch,
    POLine,
    PurchaseBudget,
    PurchaseOrder,
)
from apps.procurement.services import (
    create_po,
    match_invoice,
    post_grn,
    submit_budget,
)
from apps.core.exceptions import DomainError
from apps.users.models import User

pytestmark = pytest.mark.django_db


@pytest.fixture
def manager_user(db) -> User:
    """A user with the MANAGER role."""
    return User.objects.create_user(
        email="manager@test.local",
        password="pw",
        full_name="Manager",
        role=User.Role.MANAGER,
    )


@pytest.fixture
def requester_user(db) -> User:
    """A user with the RECEIVING_OFFICER role."""
    return User.objects.create_user(
        email="requester@test.local",
        password="pw",
        full_name="Requester",
        role=User.Role.RECEIVING_OFFICER,
    )


@pytest.fixture
def category(db) -> Category:
    """A product category."""
    return Category.objects.create(name="TestCat")


@pytest.fixture
def product(db, category) -> Product:
    """A simple product for testing."""
    return Product.objects.create(
        code="TESTPROD",
        name="Test Product",
        category=category,
        stock_uom="kg",
        purchase_uom="kg",
        recipe_uom="kg",
    )


@pytest.fixture
def supplier(db) -> Supplier:
    """A supplier with no email address (manual contact path)."""
    return Supplier.objects.create(name="Test Supplier")


@pytest.fixture
def supplier_with_email(db) -> Supplier:
    """A supplier with a valid email address."""
    return Supplier.objects.create(name="Email Supplier", email="supplier@example.com")


@pytest.fixture
def stores_location(db) -> Location:
    """A STORES-kind location for GRN stock receipt."""
    return Location.objects.create(name="Stores", kind=Location.Kind.STORES)


@pytest.fixture
def draft_budget(db, requester_user, product) -> PurchaseBudget:
    """A DRAFT budget with one line."""
    budget = PurchaseBudget.objects.create(
        requester=requester_user,
        total_estimated=Decimal("500.00"),
    )
    BudgetLine.objects.create(
        budget=budget,
        product=product,
        qty=Decimal("10.000"),
        est_unit_cost=Decimal("50.00"),
    )
    return budget


@pytest.fixture
def approved_budget(db, draft_budget, requester_user) -> PurchaseBudget:
    """An APPROVED budget ready for PO creation."""
    draft_budget.status = PurchaseBudget.Status.APPROVED
    draft_budget.save()
    return draft_budget


def test_submit_budget_creates_approval_and_notifies(
    draft_budget, requester_user, manager_user
):
    """submit_budget transitions to SUBMITTED, creates an Approval, and notifies managers."""
    with patch("apps.procurement.services.notify_role") as mock_notify:
        approval = submit_budget(budget=draft_budget, user=requester_user)

    draft_budget.refresh_from_db()
    assert draft_budget.status == PurchaseBudget.Status.SUBMITTED

    assert isinstance(approval, Approval)
    assert approval.status == Approval.Status.PENDING
    assert str(approval.subject_id) == str(draft_budget.pk)

    mock_notify.assert_called_once()
    call_kwargs = mock_notify.call_args.kwargs
    assert call_kwargs["role"] == User.Role.MANAGER
    assert call_kwargs["kind"] == Notification.Kind.APPROVAL_PENDING


def test_submit_budget_rejects_non_draft(approved_budget, requester_user):
    """submit_budget raises DomainError when the budget is not in DRAFT status."""
    with pytest.raises(DomainError):
        submit_budget(budget=approved_budget, user=requester_user)


def test_create_po_blocked_unless_budget_approved(draft_budget, supplier, requester_user, product):
    """create_po raises DomainError when the budget has not been approved."""
    lines = [{"product_id": product.pk, "qty": Decimal("5.000"), "unit_price": Decimal("10.00")}]
    with pytest.raises(DomainError):
        create_po(budget=draft_budget, supplier=supplier, lines=lines, user=requester_user)


def test_create_po_succeeds_for_approved_budget(
    approved_budget, supplier, requester_user, product
):
    """create_po creates a PO with a sequential PO number and the supplied lines."""
    lines = [{"product_id": product.pk, "qty": Decimal("5.000"), "unit_price": Decimal("10.00")}]
    po = create_po(
        budget=approved_budget, supplier=supplier, lines=lines, user=requester_user
    )

    assert isinstance(po, PurchaseOrder)
    assert po.po_number.startswith("PO-")
    assert po.lines.count() == 1
    line = po.lines.first()
    assert line.qty == Decimal("5.000")
    assert line.unit_price == Decimal("10.00")


def test_post_grn_increases_stock_and_updates_fulfilled(
    approved_budget, supplier, requester_user, product, stores_location
):
    """post_grn posts stock movements and updates fulfilled_qty on the PO line."""
    lines_data = [
        {"product_id": product.pk, "qty": Decimal("10.000"), "unit_price": Decimal("50.00")}
    ]
    po = create_po(
        budget=approved_budget, supplier=supplier, lines=lines_data, user=requester_user
    )
    po_line = po.lines.first()

    grn_lines_data = [
        {
            "po_line_id": po_line.pk,
            "qty_received": Decimal("10.000"),
            "unit_cost": Decimal("50.00"),
        }
    ]

    grn = post_grn(po=po, lines_data=grn_lines_data, received_by=requester_user)

    assert grn.status == GRN.Status.POSTED
    po_line.refresh_from_db()
    assert po_line.fulfilled_qty == Decimal("10.000")

    po.refresh_from_db()
    assert po.status == PurchaseOrder.Status.RECEIVED


def test_partial_then_full_grn(
    approved_budget, supplier, requester_user, product, stores_location
):
    """Partial receive sets PARTIALLY_RECEIVED; completing it sets RECEIVED."""
    lines_data = [
        {"product_id": product.pk, "qty": Decimal("10.000"), "unit_price": Decimal("50.00")}
    ]
    po = create_po(
        budget=approved_budget, supplier=supplier, lines=lines_data, user=requester_user
    )
    po_line = po.lines.first()

    partial_lines = [
        {
            "po_line_id": po_line.pk,
            "qty_received": Decimal("5.000"),
            "unit_cost": Decimal("50.00"),
        }
    ]
    post_grn(po=po, lines_data=partial_lines, received_by=requester_user)
    po.refresh_from_db()
    assert po.status == PurchaseOrder.Status.PARTIALLY_RECEIVED

    remaining_lines = [
        {
            "po_line_id": po_line.pk,
            "qty_received": Decimal("5.000"),
            "unit_cost": Decimal("50.00"),
        }
    ]
    post_grn(po=po, lines_data=remaining_lines, received_by=requester_user)
    po.refresh_from_db()
    assert po.status == PurchaseOrder.Status.RECEIVED


def test_invoice_mismatch_flags_discrepancy(
    approved_budget, supplier, requester_user, product, stores_location
):
    """match_invoice sets status DISCREPANCY when the invoice amount differs from the PO value."""
    lines_data = [
        {"product_id": product.pk, "qty": Decimal("10.000"), "unit_price": Decimal("50.00")}
    ]
    po = create_po(
        budget=approved_budget, supplier=supplier, lines=lines_data, user=requester_user
    )
    po_line = po.lines.first()

    grn_lines_data = [
        {
            "po_line_id": po_line.pk,
            "qty_received": Decimal("10.000"),
            "unit_cost": Decimal("50.00"),
        }
    ]
    post_grn(po=po, lines_data=grn_lines_data, received_by=requester_user)

    # Invoice amount intentionally different to PO value (500.00)
    invoice, match = match_invoice(
        po=po,
        invoice_ref="INV-9999",
        amount=Decimal("600.00"),
        user=requester_user,
    )

    assert match.status == InvoiceMatch.Status.DISCREPANCY
    assert "po_value" in match.discrepancies


def test_invoice_exact_match(
    approved_budget, supplier, requester_user, product, stores_location
):
    """match_invoice sets status MATCHED when the invoice amount equals the PO value."""
    lines_data = [
        {"product_id": product.pk, "qty": Decimal("10.000"), "unit_price": Decimal("50.00")}
    ]
    po = create_po(
        budget=approved_budget, supplier=supplier, lines=lines_data, user=requester_user
    )
    po_line = po.lines.first()

    grn_lines_data = [
        {
            "po_line_id": po_line.pk,
            "qty_received": Decimal("10.000"),
            "unit_cost": Decimal("50.00"),
        }
    ]
    post_grn(po=po, lines_data=grn_lines_data, received_by=requester_user)

    invoice, match = match_invoice(
        po=po,
        invoice_ref="INV-1111",
        amount=Decimal("500.00"),
        user=requester_user,
    )

    assert match.status == InvoiceMatch.Status.MATCHED
    assert match.discrepancies == {}

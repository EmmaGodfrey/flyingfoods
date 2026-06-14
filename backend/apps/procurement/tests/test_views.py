"""View-layer tests for the procurement module."""

from decimal import Decimal
from unittest.mock import patch

import pytest
from django.core import mail
from rest_framework.test import APIClient

from apps.masterdata.models import Category, Location, Product, Supplier
from apps.procurement.models import (
    BudgetLine,
    PurchaseBudget,
    PurchaseOrder,
    POLine,
)
from apps.procurement.services import create_po
from apps.users.models import User

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def api_client() -> APIClient:
    """Unauthenticated DRF test client."""
    return APIClient()


@pytest.fixture
def make_user(db):
    """Factory creating a user with a given role."""
    def _make(role: str, email: str | None = None) -> User:
        email = email or f"{role.lower()}test@test.local"
        return User.objects.create_user(
            email=email, password="pw", full_name=f"{role} Tester", role=role
        )
    return _make


@pytest.fixture
def auth_client(api_client, make_user):
    """Factory returning an APIClient authenticated as a given role."""
    def _auth(role: str) -> APIClient:
        user = make_user(role)
        api_client.force_authenticate(user=user)
        api_client.handler_user = user  # type: ignore[attr-defined]
        return api_client
    return _auth


@pytest.fixture
def category(db) -> Category:
    return Category.objects.create(name="ViewTestCat")


@pytest.fixture
def product(db, category) -> Product:
    return Product.objects.create(
        code="VPROD1",
        name="View Test Product",
        category=category,
        stock_uom="kg",
        purchase_uom="kg",
        recipe_uom="kg",
    )


@pytest.fixture
def supplier_no_email(db) -> Supplier:
    return Supplier.objects.create(name="No Email Supplier")


@pytest.fixture
def supplier_with_email(db) -> Supplier:
    return Supplier.objects.create(name="Email Supplier", email="orders@supplier.com")


@pytest.fixture
def stores_location(db) -> Location:
    return Location.objects.create(name="StoresView", kind=Location.Kind.STORES)


@pytest.fixture
def draft_budget(db, make_user, product) -> PurchaseBudget:
    """A DRAFT budget owned by a RECEIVING_OFFICER user."""
    requester = make_user(User.Role.RECEIVING_OFFICER, email="budgetowner@test.local")
    budget = PurchaseBudget.objects.create(
        requester=requester, total_estimated=Decimal("1000.00")
    )
    BudgetLine.objects.create(
        budget=budget, product=product, qty=Decimal("20.000"), est_unit_cost=Decimal("50.00")
    )
    return budget


@pytest.fixture
def approved_budget(db, draft_budget) -> PurchaseBudget:
    draft_budget.status = PurchaseBudget.Status.APPROVED
    draft_budget.save()
    return draft_budget


@pytest.fixture
def po_no_email(db, approved_budget, supplier_no_email, product):
    """A PO against an approved budget for a supplier without an email."""
    make_user_obj = User.objects.create_user(
        email="roforpo@test.local",
        password="pw",
        full_name="RO PO",
        role=User.Role.RECEIVING_OFFICER,
    )
    return create_po(
        budget=approved_budget,
        supplier=supplier_no_email,
        lines=[{"product_id": product.pk, "qty": Decimal("5.000"), "unit_price": Decimal("10.00")}],
        user=make_user_obj,
    )


@pytest.fixture
def po_with_email(db, approved_budget, supplier_with_email, product):
    """A PO against an approved budget for a supplier with an email."""
    make_user_obj = User.objects.create_user(
        email="roforpoemail@test.local",
        password="pw",
        full_name="RO Email PO",
        role=User.Role.RECEIVING_OFFICER,
    )
    return create_po(
        budget=approved_budget,
        supplier=supplier_with_email,
        lines=[{"product_id": product.pk, "qty": Decimal("5.000"), "unit_price": Decimal("10.00")}],
        user=make_user_obj,
    )


# ---------------------------------------------------------------------------
# Budget view tests
# ---------------------------------------------------------------------------


def test_budget_create_authenticated(auth_client, product):
    """POST /budgets/create/ with a valid payload returns 201 for any authenticated user."""
    client = auth_client(User.Role.RECEIVING_OFFICER)
    payload = {
        "total_estimated": "500.00",
        "lines": [
            {"product": str(product.pk), "qty": "10.000", "est_unit_cost": "50.00"}
        ],
    }
    response = client.post("/api/budgets/create/", data=payload, format="json")
    assert response.status_code == 201


def test_budget_create_returns_id(auth_client, product):
    """POST /budgets/create/ response contains the new budget id."""
    client = auth_client(User.Role.MANAGER)
    payload = {
        "total_estimated": "200.00",
        "lines": [
            {"product": str(product.pk), "qty": "4.000", "est_unit_cost": "50.00"}
        ],
    }
    response = client.post("/api/budgets/create/", data=payload, format="json")
    assert response.status_code == 201
    data = response.json()
    assert "id" in data["data"]


def test_budget_submit(auth_client, draft_budget):
    """POST /budgets/{id}/submit/ transitions the budget to SUBMITTED."""
    client = auth_client(User.Role.RECEIVING_OFFICER)
    with patch("apps.procurement.services.notify_role"):
        response = client.post(f"/api/budgets/{draft_budget.pk}/submit/")
    assert response.status_code == 200
    draft_budget.refresh_from_db()
    assert draft_budget.status == PurchaseBudget.Status.SUBMITTED


def test_unauthenticated_401(api_client):
    """GET /budgets/ without a token returns 401."""
    response = api_client.get("/api/budgets/")
    assert response.status_code == 401


def test_wrong_role_403(auth_client):
    """GET /budgets/ with a CHEF role returns 403 (IsProcurementStaff blocks it)."""
    client = auth_client(User.Role.CHEF)
    response = client.get("/api/budgets/")
    assert response.status_code == 403


def test_budget_list_accessible_to_procurement_staff(auth_client):
    """GET /budgets/ returns 200 for a RECEIVING_OFFICER."""
    client = auth_client(User.Role.RECEIVING_OFFICER)
    response = client.get("/api/budgets/")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Purchase Order send tests
# ---------------------------------------------------------------------------


def test_send_po_no_email_supplier(auth_client, po_no_email):
    """POST /purchase-orders/{id}/send/ with no-email supplier sets MANUAL_CONTACT_REQUIRED."""
    client = auth_client(User.Role.RECEIVING_OFFICER)
    response = client.post(f"/api/purchase-orders/{po_no_email.pk}/send/")
    assert response.status_code == 200
    po_no_email.refresh_from_db()
    assert po_no_email.status == PurchaseOrder.Status.MANUAL_CONTACT_REQUIRED


def test_send_po_with_email(auth_client, po_with_email):
    """POST /purchase-orders/{id}/send/ with an email supplier dispatches an email."""
    client = auth_client(User.Role.RECEIVING_OFFICER)
    response = client.post(f"/api/purchase-orders/{po_with_email.pk}/send/")
    assert response.status_code == 200
    po_with_email.refresh_from_db()
    assert po_with_email.status == PurchaseOrder.Status.SENT
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["orders@supplier.com"]


# ---------------------------------------------------------------------------
# Purchase Order list test
# ---------------------------------------------------------------------------


def test_po_list_accessible_to_procurement_staff(auth_client):
    """GET /purchase-orders/ returns 200 for a MANAGER."""
    client = auth_client(User.Role.MANAGER)
    response = client.get("/api/purchase-orders/")
    assert response.status_code == 200


def test_po_list_forbidden_for_chef(auth_client):
    """GET /purchase-orders/ returns 403 for a CHEF."""
    client = auth_client(User.Role.CHEF)
    response = client.get("/api/purchase-orders/")
    assert response.status_code == 403

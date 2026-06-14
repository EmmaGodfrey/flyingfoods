"""Shared fixtures for Pastel integration tests."""

import uuid
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.core.models import OutboxRecord
from apps.masterdata.models import Category, Location, Product
from apps.users.models import User


@pytest.fixture
def product(db) -> Product:
    """A product with a pastel_code for reconciliation tests."""
    category = Category.objects.create(name="Pastel Test Cat")
    return Product.objects.create(
        code="PT001",
        name="Pastel Test Product",
        category=category,
        stock_uom="each",
        purchase_uom="each",
        recipe_uom="each",
        reorder_level=Decimal("5"),
        pastel_code="PT001",
    )


@pytest.fixture
def locations(db) -> dict[str, Location]:
    """Standard three-location set."""
    return {
        "stores": Location.objects.create(name="Stores", kind=Location.Kind.STORES),
        "kitchen": Location.objects.create(name="Kitchen", kind=Location.Kind.KITCHEN),
        "unit": Location.objects.create(name="Unit", kind=Location.Kind.UNIT),
    }


@pytest.fixture
def make_user(db):
    """Factory creating a user with a given role."""

    def _make(role: str, email: str | None = None) -> User:
        email = email or f"pastel-{role.lower()}@test.local"
        return User.objects.create_user(
            email=email,
            password="pw",
            full_name=f"{role} Tester",
            role=role,
        )

    return _make


@pytest.fixture
def auth_client(make_user):
    """Factory returning an authenticated APIClient for a given role."""

    def _auth(role: str) -> APIClient:
        client = APIClient()
        user = make_user(role)
        client.force_authenticate(user=user)
        return client

    return _auth


@pytest.fixture
def pending_outbox(db) -> OutboxRecord:
    """A PENDING OutboxRecord ready to be drained."""
    return OutboxRecord.objects.create(
        entity_type="GRN",
        entity_id=uuid.uuid4(),
        payload={"document_type": "GRN", "document_id": str(uuid.uuid4()), "lines": []},
        status=OutboxRecord.Status.PENDING,
    )

"""Shared pytest fixtures: API client and one user per role."""

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.masterdata.models import Category, Location, Product
from apps.users.models import User


@pytest.fixture
def api_client() -> APIClient:
    """Unauthenticated DRF test client."""
    return APIClient()


@pytest.fixture
def make_user(db):
    """Factory creating a user with a given role."""

    def _make(role: str, email: str | None = None) -> User:
        email = email or f"{role.lower()}@test.local"
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
def locations(db) -> dict[str, Location]:
    """The three seeded inventory locations."""
    return {
        "stores": Location.objects.create(name="Stores", kind=Location.Kind.STORES),
        "kitchen": Location.objects.create(name="Kitchen", kind=Location.Kind.KITCHEN),
        "unit": Location.objects.create(name="Unit", kind=Location.Kind.UNIT),
    }


@pytest.fixture
def product(db) -> Product:
    """A simple product with 1:1 unit conversions."""
    category = Category.objects.create(name="Test Cat")
    return Product.objects.create(
        code="P1",
        name="Test Product",
        category=category,
        stock_uom="each",
        purchase_uom="each",
        recipe_uom="each",
        reorder_level=Decimal("10"),
    )

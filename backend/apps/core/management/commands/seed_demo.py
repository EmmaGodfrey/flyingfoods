"""Seed a demo dataset: locations, roles, users, products, a published recipe.

Idempotent — safe to run repeatedly. Prints the demo password on completion.
"""

import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.models import ReasonCode, ThresholdConfig
from apps.inventory.services import MovementLine, post_movements
from apps.masterdata.models import Category, Location, Product, Supplier
from apps.menu.models import MenuItem
from apps.menu.services import create_recipe_version, publish_version
from apps.users.models import User

DEMO_PASSWORD = "flyingfoods123"

DEMO_USERS = [
    ("chef@ff.local", "Chef Demo", User.Role.CHEF),
    ("waiter@ff.local", "Waiter Demo", User.Role.WAITER),
    ("storekeeper@ff.local", "Storekeeper Demo", User.Role.STOREKEEPER),
    ("receiving@ff.local", "Receiving Demo", User.Role.RECEIVING_OFFICER),
    ("unitissuer@ff.local", "Unit Issuer Demo", User.Role.UNIT_ISSUER),
    ("restissuer@ff.local", "Restaurant Issuer Demo", User.Role.RESTAURANT_ISSUER),
    ("manager@ff.local", "Manager Demo", User.Role.MANAGER),
    ("admin@ff.local", "Admin Demo", User.Role.ADMIN),
]


class Command(BaseCommand):
    """Populate the database with a runnable demo dataset."""

    help = "Seed demo locations, users, products, and a published recipe."

    @transaction.atomic
    def handle(self, *args: object, **options: object) -> None:
        """Create demo data idempotently."""
        stores = self._location("Restaurant Stores", Location.Kind.STORES)
        self._location("Restaurant Kitchen", Location.Kind.KITCHEN)
        self._location("In-Flight Unit", Location.Kind.UNIT)

        for email, name, role in DEMO_USERS:
            if not User.objects.filter(email=email).exists():
                User.objects.create_user(
                    email=email, password=DEMO_PASSWORD, full_name=name, role=role,
                    is_staff=(role == User.Role.ADMIN),
                )

        for category, label in [
            (ReasonCode.Category.WASTAGE, "Dropped / spoiled"),
            (ReasonCode.Category.RETURN, "Customer complaint"),
            (ReasonCode.Category.OVERRIDE, "Manager override"),
            (ReasonCode.Category.ISSUE_DAY, "Urgent off-schedule need"),
            (ReasonCode.Category.VARIANCE, "GRN short delivery"),
        ]:
            ReasonCode.objects.get_or_create(category=category, label=label)

        for scope in ThresholdConfig.Scope.values:
            ThresholdConfig.objects.get_or_create(
                scope=scope, is_active=True, defaults={"amount": Decimal("500.00")}
            )

        Supplier.objects.get_or_create(
            name="Fresh Produce Co",
            defaults={"email": "orders@freshproduce.local", "contact_name": "Sam Green"},
        )

        category = Category.objects.get_or_create(name="Dry Goods")[0]
        produce = Category.objects.get_or_create(name="Produce")[0]
        patty = self._product("BEEF-PATTY", "Beef patty", produce, "each")
        bun = self._product("BURGER-BUN", "Burger bun", category, "each")

        # Opening balance at Stores so demo sales can deduct.
        for product in (patty, bun):
            post_movements(
                document_type="OpeningBalance",
                document_id=product.pk,
                lines=[
                    MovementLine(
                        product_id=product.pk,
                        location_id=stores.pk,
                        qty_delta=Decimal("200"),
                        movement_type="GRN_RECEIPT",
                        unit_cost=Decimal("2.50"),
                    )
                ],
                allow_negative=True,
            )

        burger = MenuItem.objects.get_or_create(
            pos_code="BURGER", defaults={"name": "Beef Burger", "category": "Mains"}
        )[0]
        if not burger.recipe_versions.exists():
            version = create_recipe_version(
                menu_item=burger,
                lines=[(patty.pk, Decimal("1")), (bun.pk, Decimal("1"))],
                selling_price=Decimal("12.00"),
            )
            publish_version(version=version, effective_from=datetime.date(2020, 1, 1))

        self.stdout.write(self.style.SUCCESS(f"Demo data seeded. Password: {DEMO_PASSWORD}"))

    def _location(self, name: str, kind: str) -> Location:
        """Get or create a location by name."""
        return Location.objects.get_or_create(name=name, defaults={"kind": kind})[0]

    def _product(self, code: str, name: str, category: Category, uom: str) -> Product:
        """Get or create a product with matching UoMs."""
        return Product.objects.get_or_create(
            code=code,
            defaults={
                "name": name,
                "category": category,
                "stock_uom": uom,
                "purchase_uom": uom,
                "recipe_uom": uom,
                "reorder_level": Decimal("20"),
            },
        )[0]

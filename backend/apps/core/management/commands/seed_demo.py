"""Seed a demo dataset: locations, users, products, recipes, and live activity.

Idempotent — safe to run repeatedly. Reference data uses get_or_create; the
transactional activity (sales, wastage, issues, transfers, procurement) only
runs on the first seed, gated on there being no sale events yet. Prints the
demo password on completion.
"""

import datetime
from decimal import Decimal
from typing import Optional

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.core.models import Approval, ReasonCode, ThresholdConfig
from apps.core.services import decide_approval
from apps.inventory.models import StockBalance, Transfer
from apps.inventory.services import (
    MovementLine,
    create_issue_note,
    post_issue_note,
    post_movements,
    post_transfer,
)
from apps.kitchen.models import Order
from apps.kitchen.services import mark_ready, mark_served, start_order
from apps.masterdata.models import Category, Location, Product, Supplier
from apps.menu.models import MenuItem
from apps.menu.services import create_recipe_version, publish_version
from apps.pos_ingest.models import SaleEvent
from apps.pos_ingest.services import ingest_sale_event
from apps.procurement.models import BudgetLine, PurchaseBudget
from apps.procurement.services import create_po, post_grn, send_po, submit_budget
from apps.users.models import User
from apps.wastage.services import create_wastage

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

# (code, name, category, uom, reorder_level, opening_qty). Opening qty below the
# reorder level seeds a visible reorder flag on the Stock screen.
DEMO_PRODUCTS = [
    ("BEEF-PATTY", "Beef patty", "Meat", "each", 20, 200),
    ("CHICKEN-BREAST", "Chicken breast", "Meat", "each", 30, 120),
    ("BURGER-BUN", "Burger bun", "Dry Goods", "each", 20, 200),
    ("CHEESE-SLICE", "Cheese slice", "Dairy", "each", 50, 300),
    ("LETTUCE", "Lettuce", "Produce", "kg", 10, 25),
    ("TOMATO", "Tomato", "Produce", "kg", 15, 40),
    ("FRIES-PACK", "Fries pack", "Dry Goods", "kg", 25, 80),
    ("COOKING-OIL", "Cooking oil", "Dry Goods", "litre", 20, 60),
    ("COLA-CAN", "Cola can", "Beverages", "each", 40, 240),
    ("MILK", "Milk", "Dairy", "litre", 10, 6),
    ("COFFEE-BEANS", "Coffee beans", "Beverages", "kg", 5, 3),
]

DEMO_SUPPLIERS = [
    ("Fresh Produce Co", "orders@freshproduce.local", "Sam Green"),
    ("Metro Cash & Carry", "sales@metro.local", "Joan Patel"),
    ("City Beverages", "orders@citybev.local", "Themba Ndlovu"),
]

# (pos_code, name, selling_price, [(product_code, qty)])
DEMO_RECIPES = [
    ("BURGER", "Beef Burger", "12.00", [("BEEF-PATTY", "1"), ("BURGER-BUN", "1"), ("CHEESE-SLICE", "1")]),
    ("CHK-BURGER", "Chicken Burger", "13.50", [("CHICKEN-BREAST", "1"), ("BURGER-BUN", "1"), ("LETTUCE", "0.05")]),
    ("FRIES", "Fries", "5.00", [("FRIES-PACK", "0.2"), ("COOKING-OIL", "0.05")]),
    ("CAPPUCCINO", "Cappuccino", "4.00", [("COFFEE-BEANS", "0.02"), ("MILK", "0.15")]),
]


class Command(BaseCommand):
    """Populate the database with a runnable demo dataset."""

    help = "Seed demo locations, users, products, recipes, and live activity."

    @transaction.atomic
    def handle(self, *args: object, **options: object) -> None:
        """Create demo data idempotently."""
        self.stores = self._location("Restaurant Stores", Location.Kind.STORES)
        self.kitchen = self._location("Restaurant Kitchen", Location.Kind.KITCHEN)
        self.unit = self._location("In-Flight Unit", Location.Kind.UNIT)

        self._users()
        self._reason_codes()
        self._thresholds()
        self._suppliers()
        self.products = self._products()
        self._opening_balances()
        self._recipes()

        if not SaleEvent.objects.exists():
            self._sales_and_service()
            self._wastage()
            self._issue_and_transfer()
            self._procurement()

        self.stdout.write(self.style.SUCCESS(f"Demo data seeded. Password: {DEMO_PASSWORD}"))

    # -- reference data -----------------------------------------------------

    def _location(self, name: str, kind: str) -> Location:
        """Get or create a location by name."""
        return Location.objects.get_or_create(name=name, defaults={"kind": kind})[0]

    def _users(self) -> None:
        """Create the eight demo role users if absent."""
        for email, name, role in DEMO_USERS:
            if not User.objects.filter(email=email).exists():
                User.objects.create_user(
                    email=email, password=DEMO_PASSWORD, full_name=name, role=role,
                    is_staff=(role == User.Role.ADMIN),
                )

    def _reason_codes(self) -> None:
        """Seed one reason code per category."""
        for category, label in [
            (ReasonCode.Category.WASTAGE, "Dropped / spoiled"),
            (ReasonCode.Category.RETURN, "Customer complaint"),
            (ReasonCode.Category.OVERRIDE, "Manager override"),
            (ReasonCode.Category.ISSUE_DAY, "Urgent off-schedule need"),
            (ReasonCode.Category.VARIANCE, "GRN short delivery"),
        ]:
            ReasonCode.objects.get_or_create(category=category, label=label)

    def _thresholds(self) -> None:
        """Seed an active approval threshold per scope."""
        for scope in ThresholdConfig.Scope.values:
            ThresholdConfig.objects.get_or_create(
                scope=scope, is_active=True, defaults={"amount": Decimal("500.00")}
            )

    def _suppliers(self) -> None:
        """Seed the demo suppliers with contact emails."""
        for name, email, contact in DEMO_SUPPLIERS:
            Supplier.objects.get_or_create(
                name=name, defaults={"email": email, "contact_name": contact}
            )

    def _products(self) -> dict[str, Product]:
        """Get or create every demo product, keyed by code."""
        products: dict[str, Product] = {}
        for code, name, category, uom, reorder, _qty in DEMO_PRODUCTS:
            cat = Category.objects.get_or_create(name=category)[0]
            products[code] = Product.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "category": cat,
                    "stock_uom": uom,
                    "purchase_uom": uom,
                    "recipe_uom": uom,
                    "reorder_level": Decimal(str(reorder)),
                },
            )[0]
        return products

    def _opening_balances(self) -> None:
        """Post an opening balance at Stores for any product lacking one."""
        for code, _n, _c, _u, _r, qty in DEMO_PRODUCTS:
            product = self.products[code]
            if StockBalance.objects.filter(product=product, location=self.stores).exists():
                continue
            post_movements(
                document_type="OpeningBalance",
                document_id=product.pk,
                lines=[
                    MovementLine(
                        product_id=product.pk,
                        location_id=self.stores.pk,
                        qty_delta=Decimal(str(qty)),
                        movement_type="GRN_RECEIPT",
                        unit_cost=Decimal("2.50"),
                    )
                ],
                allow_negative=True,
            )

    def _recipes(self) -> None:
        """Create and publish a recipe version per demo menu item."""
        for pos_code, name, price, lines in DEMO_RECIPES:
            item = MenuItem.objects.get_or_create(
                pos_code=pos_code, defaults={"name": name, "category": "Mains"}
            )[0]
            if item.recipe_versions.exists():
                continue
            version = create_recipe_version(
                menu_item=item,
                lines=[(self.products[code].pk, Decimal(qty)) for code, qty in lines],
                selling_price=Decimal(price),
            )
            publish_version(version=version, effective_from=datetime.date(2020, 1, 1))

    # -- transactional activity (first run only) ---------------------------

    def _sales_and_service(self) -> None:
        """Ingest sales and walk a few orders through the kitchen lifecycle."""
        chef = User.objects.filter(role=User.Role.CHEF).first()
        waiter = User.objects.filter(role=User.Role.WAITER).first()
        plan = [
            ("BURGER", 2, "T1"), ("FRIES", 2, "T1"), ("CHK-BURGER", 1, "T2"),
            ("CAPPUCCINO", 1, "T3"), ("BURGER", 1, "T4"),
        ]
        events = [self._sale(f"DEMO-{i:03d}", table, pos_code, qty) for i, (pos_code, qty, table) in enumerate(plan)]

        # Lifecycle: served, served, ready, started, leave the rest ingested.
        orders = [Order.objects.filter(sale_event=e).first() for e in events]
        orders = [o for o in orders if o is not None]
        if len(orders) >= 1:
            mark_served(order=mark_ready(order=start_order(order=orders[0], user=chef), user=chef), user=waiter)
        if len(orders) >= 2:
            mark_served(order=mark_ready(order=start_order(order=orders[1], user=chef), user=chef), user=waiter)
        if len(orders) >= 3:
            mark_ready(order=start_order(order=orders[2], user=chef), user=chef)
        if len(orders) >= 4:
            start_order(order=orders[3], user=chef)

    def _sale(self, sale_id: str, table: str, pos_code: str, qty: int) -> SaleEvent:
        """Ingest a single POS sale and return the created event."""
        return ingest_sale_event(
            {
                "pos_sale_id": sale_id,
                "sold_at": timezone.now().isoformat(),
                "cashier": "POS-1",
                "table_ref": table,
                "lines": [{"pos_code": pos_code, "qty": qty}],
                "totals": {"grand": "0.00"},
            }
        )

    def _wastage(self) -> None:
        """Log two small wastage entries that post immediately."""
        chef = User.objects.filter(role=User.Role.CHEF).first()
        reason = ReasonCode.objects.filter(category=ReasonCode.Category.WASTAGE).first()
        create_wastage(
            entry_type="SPOILAGE", product_id=self.products["LETTUCE"].pk,
            location_id=self.kitchen.pk, qty=Decimal("1.5"), reason_code=reason,
            logged_by=chef, note="Wilted overnight",
        )
        create_wastage(
            entry_type="BREAKAGE", product_id=self.products["MILK"].pk,
            location_id=self.kitchen.pk, qty=Decimal("0.5"), reason_code=reason,
            logged_by=chef, note="Dropped carton",
        )

    def _issue_and_transfer(self) -> None:
        """Post one Stores->Kitchen issue and one Stores->Unit transfer."""
        storekeeper = User.objects.filter(role=User.Role.STOREKEEPER).first()
        note = create_issue_note(
            source=self.stores,
            destination=self.kitchen,
            requested_by=storekeeper,
            lines=[(self.products["BEEF-PATTY"].pk, Decimal("20")), (self.products["BURGER-BUN"].pk, Decimal("20"))],
        )
        post_issue_note(issue_note=note, posted_by=storekeeper)

        transfer = Transfer.objects.create(
            source=self.stores, destination=self.unit, requested_by=storekeeper
        )
        TransferLine = transfer.lines.model
        TransferLine.objects.bulk_create([
            TransferLine(transfer=transfer, product=self.products["COLA-CAN"], qty=Decimal("48")),
        ])
        post_transfer(transfer=transfer, posted_by=storekeeper, skip_approval=True)

    def _procurement(self) -> None:
        """Seed one approved budget->PO->GRN chain and one pending budget."""
        manager = User.objects.filter(role=User.Role.MANAGER).first()
        receiver = User.objects.filter(role=User.Role.RECEIVING_OFFICER).first()
        supplier = Supplier.objects.filter(email__gt="").first()

        approved = self._budget(manager, [("CHICKEN-BREAST", 50, "3.00"), ("FRIES-PACK", 30, "2.00")])
        approval = submit_budget(budget=approved, user=manager)
        decide_approval(approval=approval, decided_by=manager, decision=Approval.Status.APPROVED)
        approved.refresh_from_db()  # decide_approval updated the budget via its GFK copy

        po = create_po(
            budget=approved,
            supplier=supplier,
            lines=[
                {"product_id": self.products["CHICKEN-BREAST"].pk, "qty": Decimal("50"), "unit_price": Decimal("3.00")},
                {"product_id": self.products["FRIES-PACK"].pk, "qty": Decimal("30"), "unit_price": Decimal("2.00")},
            ],
            user=manager,
        )
        send_po(po=po, user=manager)
        post_grn(
            po=po,
            lines_data=[
                {"po_line_id": line.pk, "qty_received": line.qty, "unit_cost": line.unit_price}
                for line in po.lines.all()
            ],
            received_by=receiver,
        )

        # A second budget left pending, so the Approvals queue has a live item.
        pending = self._budget(manager, [("COOKING-OIL", 40, "4.00")])
        submit_budget(budget=pending, user=manager)

    def _budget(self, requester: User, lines: list[tuple[str, int, str]]) -> PurchaseBudget:
        """Create a draft budget with lines and a summed estimate."""
        total = sum((Decimal(str(q)) * Decimal(c) for _code, q, c in lines), Decimal("0"))
        budget = PurchaseBudget.objects.create(requester=requester, total_estimated=total)
        BudgetLine.objects.bulk_create([
            BudgetLine(budget=budget, product=self.products[code], qty=Decimal(str(q)), est_unit_cost=Decimal(c))
            for code, q, c in lines
        ])
        return budget

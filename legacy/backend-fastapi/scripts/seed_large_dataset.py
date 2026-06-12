"""Seed a larger branch-scoped ERP dataset for workflow and load testing."""

from __future__ import annotations

import argparse
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select

from app.db.models import (
    Branch,
    Category,
    GoodsReceivedNote,
    GoodsReceivedNoteLineItem,
    MovementType,
    Product,
    PurchaseOrder,
    PurchaseOrderLineItem,
    PurchaseOrderStatus,
    Sale,
    SaleLineItem,
    StockMovement,
    Supplier,
    Unit,
    User,
    UserRole,
)
from app.db.session import SessionLocal
from app.services.security import hash_password


@dataclass
class SeedSummary:
    created_users: int = 0
    created_categories: int = 0
    created_units: int = 0
    created_suppliers: int = 0
    created_products: int = 0
    created_movements: int = 0
    created_purchase_orders: int = 0
    created_grns: int = 0
    created_sales: int = 0


def _money(value: float) -> Decimal:
    return Decimal(f"{value:.2f}")


async def seed_large_dataset(
    *,
    branch_code: str,
    branch_name: str,
    categories: int,
    units: int,
    suppliers: int,
    products: int,
    movements: int,
    purchase_orders: int,
    sales: int,
    seed_value: int,
) -> SeedSummary:
    random.seed(seed_value)
    summary = SeedSummary()

    async with SessionLocal() as session:
        branch = (await session.execute(select(Branch).where(Branch.code == branch_code))).scalar_one_or_none()
        if branch is None:
            branch = Branch(code=branch_code, name=branch_name, is_active=True)
            session.add(branch)
            await session.flush()

        user_specs = [
            ("superadmin@example.com", UserRole.superadmin.value),
            ("admin@example.com", UserRole.admin.value),
            ("manager@example.com", UserRole.manager.value),
            ("inventory@example.com", UserRole.inventory_officer.value),
            ("cashier@example.com", UserRole.cashier.value),
        ]
        for email, role in user_specs:
            user = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
            if user is None:
                user = User(
                    email=email,
                    hashed_password=hash_password("password123"),
                    role=role,
                    branch_id=branch.id,
                    is_active=True,
                )
                session.add(user)
                summary.created_users += 1
            else:
                user.hashed_password = hash_password("password123")
                user.role = role
                user.branch_id = branch.id
                user.is_active = True

        await session.flush()

        manager_user = (await session.execute(select(User).where(User.email == "manager@example.com"))).scalar_one()
        inventory_user = (await session.execute(select(User).where(User.email == "inventory@example.com"))).scalar_one()
        cashier_user = (await session.execute(select(User).where(User.email == "cashier@example.com"))).scalar_one()

        existing_categories = (
            await session.execute(select(Category).where(Category.branch_id == branch.id).order_by(Category.id))
        ).scalars().all()
        while len(existing_categories) < categories:
            idx = len(existing_categories) + 1
            category = Category(branch_id=branch.id, name=f"Seed Category {idx:03d}", is_active=True)
            session.add(category)
            existing_categories.append(category)
            summary.created_categories += 1

        existing_units = (await session.execute(select(Unit).where(Unit.branch_id == branch.id).order_by(Unit.id))).scalars().all()
        while len(existing_units) < units:
            idx = len(existing_units) + 1
            unit = Unit(branch_id=branch.id, name=f"Seed Unit {idx:03d}", symbol=f"u{idx:02d}", is_active=True)
            session.add(unit)
            existing_units.append(unit)
            summary.created_units += 1

        existing_suppliers = (
            await session.execute(select(Supplier).where(Supplier.branch_id == branch.id).order_by(Supplier.id))
        ).scalars().all()
        while len(existing_suppliers) < suppliers:
            idx = len(existing_suppliers) + 1
            supplier = Supplier(
                branch_id=branch.id,
                name=f"Seed Supplier {idx:03d}",
                contact_name=f"Contact {idx:03d}",
                phone=f"555-{2000 + idx}",
                email=f"supplier{idx:03d}@seed.local",
                is_active=True,
            )
            session.add(supplier)
            existing_suppliers.append(supplier)
            summary.created_suppliers += 1

        await session.flush()

        existing_products = (
            await session.execute(select(Product).where(Product.branch_id == branch.id).order_by(Product.id))
        ).scalars().all()
        while len(existing_products) < products:
            idx = len(existing_products) + 1
            cost = _money(random.uniform(0.5, 40.0))
            margin = _money(random.uniform(0.2, 0.9))
            product = Product(
                branch_id=branch.id,
                category_id=random.choice(existing_categories).id,
                unit_id=random.choice(existing_units).id,
                supplier_id=random.choice(existing_suppliers).id,
                name=f"Seed Product {idx:04d}",
                sku=f"SEED-{idx:04d}",
                barcode=f"9900{idx:08d}",
                reorder_level=_money(random.uniform(5, 50)),
                cost_price=cost,
                selling_price=cost + margin,
                is_active=True,
            )
            session.add(product)
            existing_products.append(product)
            summary.created_products += 1

        await session.flush()

        now = datetime.now(timezone.utc)

        for idx in range(movements):
            product = random.choice(existing_products)
            movement_kind = random.choice([MovementType.receive.value, MovementType.adjustment.value, MovementType.sale.value])
            if movement_kind == MovementType.sale.value:
                qty = _money(-abs(random.uniform(1, 6)))
                actor_id = cashier_user.id
            else:
                qty = _money(abs(random.uniform(4, 30)))
                actor_id = inventory_user.id
            session.add(
                StockMovement(
                    product_id=product.id,
                    branch_id=branch.id,
                    qty=qty,
                    movement_type=movement_kind,
                    reference_id=f"seed-move-{idx + 1:06d}",
                    created_by=actor_id,
                    created_at=now - timedelta(minutes=idx),
                )
            )
            summary.created_movements += 1

        await session.flush()

        for idx in range(purchase_orders):
            created_at = now - timedelta(days=random.randint(1, 90), minutes=idx)
            status = random.choices(
                [
                    PurchaseOrderStatus.draft.value,
                    PurchaseOrderStatus.submitted.value,
                    PurchaseOrderStatus.approved.value,
                    PurchaseOrderStatus.received.value,
                ],
                weights=[1, 2, 3, 4],
                k=1,
            )[0]
            po = PurchaseOrder(
                branch_id=branch.id,
                supplier_id=random.choice(existing_suppliers).id,
                status=status,
                created_by_user_id=manager_user.id,
                submitted_by_user_id=manager_user.id if status != PurchaseOrderStatus.draft.value else None,
                approved_by_user_id=manager_user.id
                if status in {PurchaseOrderStatus.approved.value, PurchaseOrderStatus.received.value}
                else None,
                notes=f"Seed PO {idx + 1:04d}",
                submitted_at=created_at + timedelta(hours=1) if status != PurchaseOrderStatus.draft.value else None,
                approved_at=created_at + timedelta(hours=3)
                if status in {PurchaseOrderStatus.approved.value, PurchaseOrderStatus.received.value}
                else None,
                received_at=created_at + timedelta(days=2) if status == PurchaseOrderStatus.received.value else None,
                created_at=created_at,
            )
            session.add(po)
            await session.flush()

            po_lines: list[PurchaseOrderLineItem] = []
            for line_idx in range(random.randint(1, 3)):
                product = random.choice(existing_products)
                ordered_qty = _money(random.uniform(5, 40))
                line = PurchaseOrderLineItem(
                    purchase_order_id=po.id,
                    branch_id=branch.id,
                    product_id=product.id,
                    quantity=ordered_qty,
                    unit_price=product.cost_price,
                    received_quantity=ordered_qty if status == PurchaseOrderStatus.received.value else Decimal("0.00"),
                )
                session.add(line)
                po_lines.append(line)

            await session.flush()

            if status == PurchaseOrderStatus.received.value:
                grn = GoodsReceivedNote(
                    purchase_order_id=po.id,
                    branch_id=branch.id,
                    received_by_user_id=inventory_user.id,
                    reference=f"SEED-GRN-{po.id:05d}",
                    notes="Generated by seed_large_dataset",
                    created_at=po.received_at or (created_at + timedelta(days=2)),
                )
                session.add(grn)
                await session.flush()

                for line in po_lines:
                    session.add(
                        GoodsReceivedNoteLineItem(
                            goods_received_note_id=grn.id,
                            purchase_order_line_item_id=line.id,
                            branch_id=branch.id,
                            product_id=line.product_id,
                            quantity_received=line.quantity,
                        )
                    )
                    session.add(
                        StockMovement(
                            product_id=line.product_id,
                            branch_id=branch.id,
                            qty=line.quantity,
                            movement_type=MovementType.receive.value,
                            reference_id=f"seed-grn-{grn.id:05d}-{line.id:05d}",
                            created_by=inventory_user.id,
                            created_at=grn.created_at,
                        )
                    )
                    summary.created_movements += 1

                summary.created_grns += 1

            summary.created_purchase_orders += 1

        await session.flush()

        for idx in range(sales):
            sale_created_at = now - timedelta(days=random.randint(0, 60), minutes=idx)
            line_count = random.randint(1, 4)
            line_items: list[tuple[Product, Decimal]] = []
            subtotal = Decimal("0.00")
            for _ in range(line_count):
                product = random.choice(existing_products)
                quantity = _money(random.uniform(1, 3))
                line_total = _money(float(product.selling_price * quantity))
                subtotal += line_total
                line_items.append((product, quantity))

            discount = _money(random.uniform(0, float(subtotal) * 0.08))
            taxable = max(subtotal - discount, Decimal("0.00"))
            tax = _money(float(taxable) * 0.07)
            total = taxable + tax

            sale = Sale(
                branch_id=branch.id,
                cashier_user_id=cashier_user.id,
                payment_method=random.choice(["cash", "card", "mobile_money"]),
                subtotal=_money(float(subtotal)),
                tax_amount=tax,
                discount_amount=discount,
                total=_money(float(total)),
                status="completed",
                created_at=sale_created_at,
            )
            session.add(sale)
            await session.flush()

            for line_idx, (product, quantity) in enumerate(line_items, start=1):
                line_total = _money(float(product.selling_price * quantity))
                session.add(
                    SaleLineItem(
                        sale_id=sale.id,
                        branch_id=branch.id,
                        product_id=product.id,
                        quantity=quantity,
                        unit_price=product.selling_price,
                        line_total=line_total,
                    )
                )
                session.add(
                    StockMovement(
                        product_id=product.id,
                        branch_id=branch.id,
                        qty=_money(-abs(float(quantity))),
                        movement_type=MovementType.sale.value,
                        reference_id=f"seed-sale-{sale.id:05d}-{line_idx:02d}",
                        created_by=cashier_user.id,
                        created_at=sale_created_at,
                    )
                )
                summary.created_movements += 1

            summary.created_sales += 1

        await session.commit()

        product_total = (
            await session.execute(select(func.count(Product.id)).where(Product.branch_id == branch.id))
        ).scalar_one()
        supplier_total = (
            await session.execute(select(func.count(Supplier.id)).where(Supplier.branch_id == branch.id))
        ).scalar_one()
        po_total = (
            await session.execute(select(func.count(PurchaseOrder.id)).where(PurchaseOrder.branch_id == branch.id))
        ).scalar_one()
        sale_total = (await session.execute(select(func.count(Sale.id)).where(Sale.branch_id == branch.id))).scalar_one()
        movement_total = (
            await session.execute(select(func.count(StockMovement.id)).where(StockMovement.branch_id == branch.id))
        ).scalar_one()

    print("Seed complete")
    print(
        {
            "branch_code": branch_code,
            "created": summary.__dict__,
            "totals": {
                "products": int(product_total),
                "suppliers": int(supplier_total),
                "purchase_orders": int(po_total),
                "sales": int(sale_total),
                "movements": int(movement_total),
            },
            "users": {
                "superadmin@example.com": "password123",
                "admin@example.com": "password123",
                "manager@example.com": "password123",
                "inventory@example.com": "password123",
                "cashier@example.com": "password123",
            },
        }
    )

    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed a larger ERP dataset")
    parser.add_argument("--branch-code", default="HQ")
    parser.add_argument("--branch-name", default="Headquarters")
    parser.add_argument("--categories", type=int, default=8)
    parser.add_argument("--units", type=int, default=5)
    parser.add_argument("--suppliers", type=int, default=30)
    parser.add_argument("--products", type=int, default=250)
    parser.add_argument("--movements", type=int, default=900)
    parser.add_argument("--purchase-orders", type=int, default=140)
    parser.add_argument("--sales", type=int, default=320)
    parser.add_argument("--seed", type=int, default=20260601)
    return parser.parse_args()


if __name__ == "__main__":
    import asyncio

    args = parse_args()
    asyncio.run(
        seed_large_dataset(
            branch_code=args.branch_code,
            branch_name=args.branch_name,
            categories=args.categories,
            units=args.units,
            suppliers=args.suppliers,
            products=args.products,
            movements=args.movements,
            purchase_orders=args.purchase_orders,
            sales=args.sales,
            seed_value=args.seed,
        )
    )

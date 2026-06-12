"""Seed helper for a minimal branch/product/BOM development dataset."""

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BillOfMaterial, Branch, Category, MovementType, Product, StockMovement, Supplier, Unit


async def seed_week3_basics(session: AsyncSession) -> None:
    """Seed a tiny branch-scoped catalog for local development."""
    branch = Branch(code="HQ", name="Headquarters")
    session.add(branch)
    await session.flush()

    unit_piece = Unit(branch_id=branch.id, name="Piece", symbol="pc")
    category_food = Category(branch_id=branch.id, name="Food")
    supplier = Supplier(branch_id=branch.id, name="Default Supplier")
    session.add_all([unit_piece, category_food, supplier])
    await session.flush()

    bun = Product(
        branch_id=branch.id,
        category_id=category_food.id,
        unit_id=unit_piece.id,
        supplier_id=supplier.id,
        name="Burger Bun",
        reorder_level=Decimal("20"),
        cost_price=Decimal("0.25"),
        selling_price=Decimal("0.00"),
    )
    patty = Product(
        branch_id=branch.id,
        category_id=category_food.id,
        unit_id=unit_piece.id,
        supplier_id=supplier.id,
        name="Beef Patty",
        reorder_level=Decimal("20"),
        cost_price=Decimal("0.80"),
        selling_price=Decimal("0.00"),
    )
    burger = Product(
        branch_id=branch.id,
        category_id=category_food.id,
        unit_id=unit_piece.id,
        supplier_id=supplier.id,
        name="Burger",
        reorder_level=Decimal("10"),
        cost_price=Decimal("1.50"),
        selling_price=Decimal("4.50"),
    )
    session.add_all([bun, patty, burger])
    await session.flush()

    session.add_all(
        [
            BillOfMaterial(branch_id=branch.id, product_id=burger.id, ingredient_id=bun.id, quantity=Decimal("2")),
            BillOfMaterial(branch_id=branch.id, product_id=burger.id, ingredient_id=patty.id, quantity=Decimal("1")),
            StockMovement(
                product_id=bun.id,
                branch_id=branch.id,
                qty=Decimal("300"),
                movement_type=MovementType.receive.value,
                reference_id="seed-receive-bun",
            ),
            StockMovement(
                product_id=patty.id,
                branch_id=branch.id,
                qty=Decimal("180"),
                movement_type=MovementType.receive.value,
                reference_id="seed-receive-patty",
            ),
        ]
    )

    await session.commit()

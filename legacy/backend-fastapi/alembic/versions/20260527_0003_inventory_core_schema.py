"""inventory core schema and indexes

Revision ID: 20260527_0003
Revises: 20260527_0002
Create Date: 2026-05-27 00:30:00
"""

# Adds branch-scoped catalog, stock ledger, and BOM structures for week 3.

from alembic import op
import sqlalchemy as sa


revision = "20260527_0003"
down_revision = "20260527_0002"
branch_labels = None
depends_on = None


NUMERIC_12_2 = sa.Numeric(12, 2)


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("branch_id", "name", name="uq_categories_branch_name"),
    )
    op.create_index(op.f("ix_categories_id"), "categories", ["id"], unique=False)
    op.create_index(op.f("ix_categories_branch_id"), "categories", ["branch_id"], unique=False)

    op.create_table(
        "units",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("symbol", sa.String(length=16), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("branch_id", "name", name="uq_units_branch_name"),
    )
    op.create_index(op.f("ix_units_id"), "units", ["id"], unique=False)
    op.create_index(op.f("ix_units_branch_id"), "units", ["branch_id"], unique=False)

    op.create_table(
        "suppliers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("contact_name", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=64), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("branch_id", "name", name="uq_suppliers_branch_name"),
    )
    op.create_index(op.f("ix_suppliers_id"), "suppliers", ["id"], unique=False)
    op.create_index(op.f("ix_suppliers_branch_id"), "suppliers", ["branch_id"], unique=False)

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("unit_id", sa.Integer(), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=True),
        sa.Column("barcode", sa.String(length=128), nullable=True),
        sa.Column("reorder_level", NUMERIC_12_2, nullable=False, server_default="0"),
        sa.Column("cost_price", NUMERIC_12_2, nullable=False, server_default="0"),
        sa.Column("selling_price", NUMERIC_12_2, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("branch_id", "name", name="uq_products_branch_name"),
    )
    op.create_index(op.f("ix_products_id"), "products", ["id"], unique=False)
    op.create_index(op.f("ix_products_branch_id"), "products", ["branch_id"], unique=False)
    op.create_index(op.f("ix_products_category_id"), "products", ["category_id"], unique=False)
    op.create_index(op.f("ix_products_unit_id"), "products", ["unit_id"], unique=False)
    op.create_index(op.f("ix_products_supplier_id"), "products", ["supplier_id"], unique=False)

    op.create_table(
        "stock_movements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("qty", NUMERIC_12_2, nullable=False),
        sa.Column("movement_type", sa.String(length=32), nullable=False),
        sa.Column("reference_id", sa.String(length=64), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(op.f("ix_stock_movements_id"), "stock_movements", ["id"], unique=False)
    op.create_index(op.f("ix_stock_movements_product_id"), "stock_movements", ["product_id"], unique=False)
    op.create_index(op.f("ix_stock_movements_branch_id"), "stock_movements", ["branch_id"], unique=False)
    op.create_index(op.f("ix_stock_movements_created_at"), "stock_movements", ["created_at"], unique=False)
    op.create_index(
        "ix_stock_movements_product_branch",
        "stock_movements",
        ["product_id", "branch_id"],
        unique=False,
    )

    op.create_table(
        "bill_of_materials",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("ingredient_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ingredient_id"], ["products.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("product_id <> ingredient_id", name="ck_bom_product_not_self"),
        sa.UniqueConstraint("branch_id", "product_id", "ingredient_id", name="uq_bom_branch_product_ingredient"),
    )
    op.create_index(op.f("ix_bill_of_materials_id"), "bill_of_materials", ["id"], unique=False)
    op.create_index(op.f("ix_bill_of_materials_branch_id"), "bill_of_materials", ["branch_id"], unique=False)
    op.create_index(op.f("ix_bill_of_materials_product_id"), "bill_of_materials", ["product_id"], unique=False)
    op.create_index(op.f("ix_bill_of_materials_ingredient_id"), "bill_of_materials", ["ingredient_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_bill_of_materials_ingredient_id"), table_name="bill_of_materials")
    op.drop_index(op.f("ix_bill_of_materials_product_id"), table_name="bill_of_materials")
    op.drop_index(op.f("ix_bill_of_materials_branch_id"), table_name="bill_of_materials")
    op.drop_index(op.f("ix_bill_of_materials_id"), table_name="bill_of_materials")
    op.drop_table("bill_of_materials")

    op.drop_index("ix_stock_movements_product_branch", table_name="stock_movements")
    op.drop_index(op.f("ix_stock_movements_created_at"), table_name="stock_movements")
    op.drop_index(op.f("ix_stock_movements_branch_id"), table_name="stock_movements")
    op.drop_index(op.f("ix_stock_movements_product_id"), table_name="stock_movements")
    op.drop_index(op.f("ix_stock_movements_id"), table_name="stock_movements")
    op.drop_table("stock_movements")

    op.drop_index(op.f("ix_products_supplier_id"), table_name="products")
    op.drop_index(op.f("ix_products_unit_id"), table_name="products")
    op.drop_index(op.f("ix_products_category_id"), table_name="products")
    op.drop_index(op.f("ix_products_branch_id"), table_name="products")
    op.drop_index(op.f("ix_products_id"), table_name="products")
    op.drop_table("products")

    op.drop_index(op.f("ix_suppliers_branch_id"), table_name="suppliers")
    op.drop_index(op.f("ix_suppliers_id"), table_name="suppliers")
    op.drop_table("suppliers")

    op.drop_index(op.f("ix_units_branch_id"), table_name="units")
    op.drop_index(op.f("ix_units_id"), table_name="units")
    op.drop_table("units")

    op.drop_index(op.f("ix_categories_branch_id"), table_name="categories")
    op.drop_index(op.f("ix_categories_id"), table_name="categories")
    op.drop_table("categories")

"""sales POS domain tables

Revision ID: 20260528_0005
Revises: 20260528_0004
Create Date: 2026-05-28 17:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260528_0005"
down_revision = "20260528_0004"
branch_labels = None
depends_on = None


NUMERIC_12_2 = sa.Numeric(12, 2)


def upgrade() -> None:
    op.create_table(
        "sales",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("cashier_user_id", sa.Integer(), nullable=True),
        sa.Column("payment_method", sa.String(length=32), nullable=False),
        sa.Column("subtotal", NUMERIC_12_2, nullable=False),
        sa.Column("total", NUMERIC_12_2, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cashier_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(op.f("ix_sales_id"), "sales", ["id"], unique=False)
    op.create_index(op.f("ix_sales_branch_id"), "sales", ["branch_id"], unique=False)
    op.create_index(op.f("ix_sales_cashier_user_id"), "sales", ["cashier_user_id"], unique=False)
    op.create_index(op.f("ix_sales_created_at"), "sales", ["created_at"], unique=False)

    op.create_table(
        "sale_line_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sale_id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity", NUMERIC_12_2, nullable=False),
        sa.Column("unit_price", NUMERIC_12_2, nullable=False),
        sa.Column("line_total", NUMERIC_12_2, nullable=False),
        sa.ForeignKeyConstraint(["sale_id"], ["sales.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
    )
    op.create_index(op.f("ix_sale_line_items_id"), "sale_line_items", ["id"], unique=False)
    op.create_index(op.f("ix_sale_line_items_sale_id"), "sale_line_items", ["sale_id"], unique=False)
    op.create_index(op.f("ix_sale_line_items_branch_id"), "sale_line_items", ["branch_id"], unique=False)
    op.create_index(op.f("ix_sale_line_items_product_id"), "sale_line_items", ["product_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_sale_line_items_product_id"), table_name="sale_line_items")
    op.drop_index(op.f("ix_sale_line_items_branch_id"), table_name="sale_line_items")
    op.drop_index(op.f("ix_sale_line_items_sale_id"), table_name="sale_line_items")
    op.drop_index(op.f("ix_sale_line_items_id"), table_name="sale_line_items")
    op.drop_table("sale_line_items")

    op.drop_index(op.f("ix_sales_created_at"), table_name="sales")
    op.drop_index(op.f("ix_sales_cashier_user_id"), table_name="sales")
    op.drop_index(op.f("ix_sales_branch_id"), table_name="sales")
    op.drop_index(op.f("ix_sales_id"), table_name="sales")
    op.drop_table("sales")

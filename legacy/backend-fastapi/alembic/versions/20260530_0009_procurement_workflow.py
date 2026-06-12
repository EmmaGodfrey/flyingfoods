"""procurement workflow tables

Revision ID: 20260530_0009
Revises: 20260528_0008
Create Date: 2026-05-30 12:40:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260530_0009"
down_revision = "20260528_0008"
branch_labels = None
depends_on = None


NUMERIC_12_2 = sa.Numeric(12, 2)


def upgrade() -> None:
    op.create_table(
        "purchase_orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("submitted_by_user_id", sa.Integer(), nullable=True),
        sa.Column("approved_by_user_id", sa.Integer(), nullable=True),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["submitted_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(op.f("ix_purchase_orders_id"), "purchase_orders", ["id"], unique=False)
    op.create_index(op.f("ix_purchase_orders_branch_id"), "purchase_orders", ["branch_id"], unique=False)
    op.create_index(op.f("ix_purchase_orders_supplier_id"), "purchase_orders", ["supplier_id"], unique=False)
    op.create_index(op.f("ix_purchase_orders_status"), "purchase_orders", ["status"], unique=False)
    op.create_index(op.f("ix_purchase_orders_created_by_user_id"), "purchase_orders", ["created_by_user_id"], unique=False)
    op.create_index(op.f("ix_purchase_orders_submitted_by_user_id"), "purchase_orders", ["submitted_by_user_id"], unique=False)
    op.create_index(op.f("ix_purchase_orders_approved_by_user_id"), "purchase_orders", ["approved_by_user_id"], unique=False)
    op.create_index(op.f("ix_purchase_orders_created_at"), "purchase_orders", ["created_at"], unique=False)

    op.create_table(
        "purchase_order_line_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("purchase_order_id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity", NUMERIC_12_2, nullable=False),
        sa.Column("unit_price", NUMERIC_12_2, nullable=False),
        sa.Column("received_quantity", NUMERIC_12_2, nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["purchase_order_id"], ["purchase_orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
    )
    op.create_index(op.f("ix_purchase_order_line_items_id"), "purchase_order_line_items", ["id"], unique=False)
    op.create_index(op.f("ix_purchase_order_line_items_purchase_order_id"), "purchase_order_line_items", ["purchase_order_id"], unique=False)
    op.create_index(op.f("ix_purchase_order_line_items_branch_id"), "purchase_order_line_items", ["branch_id"], unique=False)
    op.create_index(op.f("ix_purchase_order_line_items_product_id"), "purchase_order_line_items", ["product_id"], unique=False)

    op.create_table(
        "goods_received_notes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("purchase_order_id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("received_by_user_id", sa.Integer(), nullable=True),
        sa.Column("reference", sa.String(length=64), nullable=True),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["purchase_order_id"], ["purchase_orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["received_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(op.f("ix_goods_received_notes_id"), "goods_received_notes", ["id"], unique=False)
    op.create_index(op.f("ix_goods_received_notes_purchase_order_id"), "goods_received_notes", ["purchase_order_id"], unique=False)
    op.create_index(op.f("ix_goods_received_notes_branch_id"), "goods_received_notes", ["branch_id"], unique=False)
    op.create_index(op.f("ix_goods_received_notes_received_by_user_id"), "goods_received_notes", ["received_by_user_id"], unique=False)
    op.create_index(op.f("ix_goods_received_notes_created_at"), "goods_received_notes", ["created_at"], unique=False)

    op.create_table(
        "goods_received_note_line_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("goods_received_note_id", sa.Integer(), nullable=False),
        sa.Column("purchase_order_line_item_id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity_received", NUMERIC_12_2, nullable=False),
        sa.ForeignKeyConstraint(["goods_received_note_id"], ["goods_received_notes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["purchase_order_line_item_id"], ["purchase_order_line_items.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
    )
    op.create_index(op.f("ix_goods_received_note_line_items_id"), "goods_received_note_line_items", ["id"], unique=False)
    op.create_index(op.f("ix_goods_received_note_line_items_goods_received_note_id"), "goods_received_note_line_items", ["goods_received_note_id"], unique=False)
    op.create_index(op.f("ix_goods_received_note_line_items_purchase_order_line_item_id"), "goods_received_note_line_items", ["purchase_order_line_item_id"], unique=False)
    op.create_index(op.f("ix_goods_received_note_line_items_branch_id"), "goods_received_note_line_items", ["branch_id"], unique=False)
    op.create_index(op.f("ix_goods_received_note_line_items_product_id"), "goods_received_note_line_items", ["product_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_goods_received_note_line_items_product_id"), table_name="goods_received_note_line_items")
    op.drop_index(op.f("ix_goods_received_note_line_items_branch_id"), table_name="goods_received_note_line_items")
    op.drop_index(op.f("ix_goods_received_note_line_items_purchase_order_line_item_id"), table_name="goods_received_note_line_items")
    op.drop_index(op.f("ix_goods_received_note_line_items_goods_received_note_id"), table_name="goods_received_note_line_items")
    op.drop_index(op.f("ix_goods_received_note_line_items_id"), table_name="goods_received_note_line_items")
    op.drop_table("goods_received_note_line_items")

    op.drop_index(op.f("ix_goods_received_notes_created_at"), table_name="goods_received_notes")
    op.drop_index(op.f("ix_goods_received_notes_received_by_user_id"), table_name="goods_received_notes")
    op.drop_index(op.f("ix_goods_received_notes_branch_id"), table_name="goods_received_notes")
    op.drop_index(op.f("ix_goods_received_notes_purchase_order_id"), table_name="goods_received_notes")
    op.drop_index(op.f("ix_goods_received_notes_id"), table_name="goods_received_notes")
    op.drop_table("goods_received_notes")

    op.drop_index(op.f("ix_purchase_order_line_items_product_id"), table_name="purchase_order_line_items")
    op.drop_index(op.f("ix_purchase_order_line_items_branch_id"), table_name="purchase_order_line_items")
    op.drop_index(op.f("ix_purchase_order_line_items_purchase_order_id"), table_name="purchase_order_line_items")
    op.drop_index(op.f("ix_purchase_order_line_items_id"), table_name="purchase_order_line_items")
    op.drop_table("purchase_order_line_items")

    op.drop_index(op.f("ix_purchase_orders_created_at"), table_name="purchase_orders")
    op.drop_index(op.f("ix_purchase_orders_approved_by_user_id"), table_name="purchase_orders")
    op.drop_index(op.f("ix_purchase_orders_submitted_by_user_id"), table_name="purchase_orders")
    op.drop_index(op.f("ix_purchase_orders_created_by_user_id"), table_name="purchase_orders")
    op.drop_index(op.f("ix_purchase_orders_status"), table_name="purchase_orders")
    op.drop_index(op.f("ix_purchase_orders_supplier_id"), table_name="purchase_orders")
    op.drop_index(op.f("ix_purchase_orders_branch_id"), table_name="purchase_orders")
    op.drop_index(op.f("ix_purchase_orders_id"), table_name="purchase_orders")
    op.drop_table("purchase_orders")

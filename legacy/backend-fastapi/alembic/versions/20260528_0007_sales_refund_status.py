"""sales refund metadata columns

Revision ID: 20260528_0007
Revises: 20260528_0006
Create Date: 2026-05-28 20:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260528_0007"
down_revision = "20260528_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sales", sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("sales", sa.Column("refunded_by_user_id", sa.Integer(), nullable=True))
    op.add_column("sales", sa.Column("refund_reason", sa.String(length=255), nullable=True))

    op.create_foreign_key(
        "fk_sales_refunded_by_user_id_users",
        "sales",
        "users",
        ["refunded_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_sales_refunded_at"), "sales", ["refunded_at"], unique=False)
    op.create_index(op.f("ix_sales_refunded_by_user_id"), "sales", ["refunded_by_user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_sales_refunded_by_user_id"), table_name="sales")
    op.drop_index(op.f("ix_sales_refunded_at"), table_name="sales")
    op.drop_constraint("fk_sales_refunded_by_user_id_users", "sales", type_="foreignkey")

    op.drop_column("sales", "refund_reason")
    op.drop_column("sales", "refunded_by_user_id")
    op.drop_column("sales", "refunded_at")

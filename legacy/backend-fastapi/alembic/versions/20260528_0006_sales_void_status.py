"""sales void metadata columns

Revision ID: 20260528_0006
Revises: 20260528_0005
Create Date: 2026-05-28 19:20:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260528_0006"
down_revision = "20260528_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sales", sa.Column("status", sa.String(length=32), nullable=False, server_default="completed"))
    op.add_column("sales", sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("sales", sa.Column("voided_by_user_id", sa.Integer(), nullable=True))
    op.add_column("sales", sa.Column("void_reason", sa.String(length=255), nullable=True))

    op.create_foreign_key(
        "fk_sales_voided_by_user_id_users",
        "sales",
        "users",
        ["voided_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_sales_voided_at"), "sales", ["voided_at"], unique=False)
    op.create_index(op.f("ix_sales_voided_by_user_id"), "sales", ["voided_by_user_id"], unique=False)

    op.alter_column("sales", "status", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_sales_voided_by_user_id"), table_name="sales")
    op.drop_index(op.f("ix_sales_voided_at"), table_name="sales")
    op.drop_constraint("fk_sales_voided_by_user_id_users", "sales", type_="foreignkey")

    op.drop_column("sales", "void_reason")
    op.drop_column("sales", "voided_by_user_id")
    op.drop_column("sales", "voided_at")
    op.drop_column("sales", "status")

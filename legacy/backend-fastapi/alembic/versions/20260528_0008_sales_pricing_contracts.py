"""sales pricing and tender contract columns

Revision ID: 20260528_0008
Revises: 20260528_0007
Create Date: 2026-05-28 21:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260528_0008"
down_revision = "20260528_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sales",
        sa.Column("tax_amount", sa.Numeric(12, 2), nullable=False, server_default=sa.text("0.00")),
    )
    op.add_column(
        "sales",
        sa.Column("discount_amount", sa.Numeric(12, 2), nullable=False, server_default=sa.text("0.00")),
    )
    op.add_column("sales", sa.Column("payment_tenders", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("sales", "payment_tenders")
    op.drop_column("sales", "discount_amount")
    op.drop_column("sales", "tax_amount")
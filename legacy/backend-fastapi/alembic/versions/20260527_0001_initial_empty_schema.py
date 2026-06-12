"""initial empty schema baseline

Revision ID: 20260527_0001
Revises:
Create Date: 2026-05-27 00:00:00
"""

# Baseline revision so all later migrations share a stable root.

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260527_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Baseline migration intentionally does not create tables.
    pass


def downgrade() -> None:
    pass

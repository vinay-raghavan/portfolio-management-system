"""Add CLOSE_POSITIONS_AND_CONTINUE to profitcutoffaction enum.

Revision ID: add_close_positions_continue
Revises: add_profit_cutoff_fields
Create Date: 2026-01-05 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'add_close_positions_continue'
down_revision: Union[str, None] = 'add_profit_cutoff_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add the missing enum value to profitcutoffaction
    op.execute("ALTER TYPE profitcutoffaction ADD VALUE IF NOT EXISTS 'CLOSE_POSITIONS_AND_CONTINUE'")


def downgrade() -> None:
    # Note: PostgreSQL doesn't support removing values from enums easily
    # This would require recreating the type, which is complex with existing data
    # For now, we'll leave the enum value in place during downgrade
    pass


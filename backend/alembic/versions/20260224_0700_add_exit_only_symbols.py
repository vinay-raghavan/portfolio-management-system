"""add exit_only_symbols to user_strategies

Revision ID: add_exit_only_symbols
Revises: add_preset_to_screeners
Create Date: 2026-02-24 07:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_exit_only_symbols'
down_revision: Union[str, None] = 'add_preset_to_screeners'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add exit_only_symbols column to user_strategies table
    # This column stores symbols that should only be exited, not entered
    # (used when screener updates remove symbols that still have open positions)
    op.add_column(
        'user_strategies',
        sa.Column('exit_only_symbols', postgresql.JSON(astext_type=sa.Text()), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('user_strategies', 'exit_only_symbols')


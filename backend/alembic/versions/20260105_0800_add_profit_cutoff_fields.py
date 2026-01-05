"""Add profit cutoff fields to user_strategies.

Revision ID: add_profit_cutoff_fields
Revises: add_execution_pnl_fields
Create Date: 2026-01-05 08:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'add_profit_cutoff_fields'
down_revision: Union[str, None] = 'add_execution_pnl_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the enum type for profit cutoff action
    op.execute("""
        CREATE TYPE profitcutoffaction AS ENUM (
            'PAUSE_STRATEGY',
            'CLOSE_POSITIONS_AND_PAUSE',
            'NOTIFY_ONLY'
        )
    """)

    # Add profit cutoff fields to user_strategies table
    op.add_column(
        'user_strategies',
        sa.Column('max_daily_profit', sa.Numeric(18, 2), nullable=True)
    )
    op.add_column(
        'user_strategies',
        sa.Column('overall_profit_target', sa.Numeric(18, 2), nullable=True)
    )
    op.add_column(
        'user_strategies',
        sa.Column(
            'profit_cutoff_action',
            sa.Enum('PAUSE_STRATEGY', 'CLOSE_POSITIONS_AND_PAUSE', 'NOTIFY_ONLY',
                    name='profitcutoffaction', create_type=False),
            nullable=False,
            server_default='PAUSE_STRATEGY'
        )
    )


def downgrade() -> None:
    # Remove profit cutoff fields from user_strategies table
    op.drop_column('user_strategies', 'profit_cutoff_action')
    op.drop_column('user_strategies', 'overall_profit_target')
    op.drop_column('user_strategies', 'max_daily_profit')

    # Drop the enum type
    op.execute("DROP TYPE profitcutoffaction")


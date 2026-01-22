"""Add strategy-level trailing stop and profit booking settings

Revision ID: strategy_risk_001
Revises: trailing_stop_001
Create Date: 2026-01-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'strategy_risk_001'
down_revision: Union[str, None] = 'trailing_stop_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add strategy-level default trailing stop and profit booking fields to user_strategies table."""
    # Add default trailing stop settings
    op.add_column(
        'user_strategies',
        sa.Column('default_trailing_stop_enabled', sa.Boolean(), nullable=False, server_default='false')
    )
    op.add_column(
        'user_strategies',
        sa.Column('default_trailing_stop_pct', sa.Numeric(10, 4), nullable=True)
    )
    
    # Add default profit booking rules (JSON)
    op.add_column(
        'user_strategies',
        sa.Column('default_profit_booking_rules', sa.JSON(), nullable=True)
    )


def downgrade() -> None:
    """Remove strategy-level default trailing stop and profit booking fields from user_strategies table."""
    op.drop_column('user_strategies', 'default_profit_booking_rules')
    op.drop_column('user_strategies', 'default_trailing_stop_pct')
    op.drop_column('user_strategies', 'default_trailing_stop_enabled')


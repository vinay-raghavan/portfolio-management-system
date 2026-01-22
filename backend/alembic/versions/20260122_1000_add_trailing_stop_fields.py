"""Add trailing stop loss fields to positions

Revision ID: trailing_stop_001
Revises: user_settings_001
Create Date: 2026-01-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'trailing_stop_001'
down_revision: Union[str, None] = 'user_settings_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add trailing stop loss fields to positions and algo_positions tables."""
    # Add trailing stop fields to positions table
    op.add_column('positions', sa.Column('trailing_stop_enabled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('positions', sa.Column('trailing_stop_pct', sa.Numeric(10, 4), nullable=True))
    op.add_column('positions', sa.Column('trailing_stop_price', sa.Numeric(18, 4), nullable=True))
    op.add_column('positions', sa.Column('highest_price_since_entry', sa.Numeric(18, 4), nullable=True))
    op.add_column('positions', sa.Column('lowest_price_since_entry', sa.Numeric(18, 4), nullable=True))
    
    # Add trailing stop fields to algo_positions table
    op.add_column('algo_positions', sa.Column('trailing_stop_enabled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('algo_positions', sa.Column('trailing_stop_pct', sa.Numeric(10, 4), nullable=True))
    op.add_column('algo_positions', sa.Column('trailing_stop_price', sa.Numeric(18, 4), nullable=True))
    op.add_column('algo_positions', sa.Column('highest_price_since_entry', sa.Numeric(18, 4), nullable=True))
    op.add_column('algo_positions', sa.Column('lowest_price_since_entry', sa.Numeric(18, 4), nullable=True))


def downgrade() -> None:
    """Remove trailing stop loss fields from positions and algo_positions tables."""
    # Remove from positions table
    op.drop_column('positions', 'lowest_price_since_entry')
    op.drop_column('positions', 'highest_price_since_entry')
    op.drop_column('positions', 'trailing_stop_price')
    op.drop_column('positions', 'trailing_stop_pct')
    op.drop_column('positions', 'trailing_stop_enabled')
    
    # Remove from algo_positions table
    op.drop_column('algo_positions', 'lowest_price_since_entry')
    op.drop_column('algo_positions', 'highest_price_since_entry')
    op.drop_column('algo_positions', 'trailing_stop_price')
    op.drop_column('algo_positions', 'trailing_stop_pct')
    op.drop_column('algo_positions', 'trailing_stop_enabled')


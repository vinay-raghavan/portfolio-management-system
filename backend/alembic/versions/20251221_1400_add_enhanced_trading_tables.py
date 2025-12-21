"""add_enhanced_trading_tables

Revision ID: add_enhanced_trading
Revises: c5cf5acab655
Create Date: 2025-12-21 14:00:00.000000+00:00

Adds:
- user_funds table for tracking virtual cash/margin
- daily_pnl table for daily performance snapshots
- product_type and realized_pnl columns to positions table
- Index for positions by product type
"""
from typing import Sequence, Union
from decimal import Decimal

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_enhanced_trading'
down_revision: Union[str, None] = 'c5cf5acab655'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create user_funds table
    op.create_table('user_funds',
        sa.Column('id', sa.UUID(as_uuid=False), nullable=False),
        sa.Column('user_id', sa.UUID(as_uuid=False), nullable=False),
        sa.Column('cash_balance', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('margin_used', sa.Numeric(precision=18, scale=4), nullable=False, 
                  server_default='0'),
        sa.Column('collateral', sa.Numeric(precision=18, scale=4), nullable=False,
                  server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), 
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), 
                  server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', name='uq_user_funds_user_id')
    )
    op.create_index(op.f('ix_user_funds_user_id'), 'user_funds', ['user_id'], unique=True)

    # Create daily_pnl table
    op.create_table('daily_pnl',
        sa.Column('id', sa.UUID(as_uuid=False), nullable=False),
        sa.Column('user_id', sa.UUID(as_uuid=False), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('total_value', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('total_cost', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('total_pnl', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('cash_balance', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('day_pnl', sa.Numeric(precision=18, scale=4), nullable=False,
                  server_default='0'),
        sa.Column('trades_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('positions_snapshot', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), 
                  server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_daily_pnl_user_date', 'daily_pnl', ['user_id', 'date'], unique=True)

    # Add new columns to positions table
    op.add_column('positions', 
        sa.Column('product_type', sa.String(length=10), nullable=False, 
                  server_default='DELIVERY')
    )
    op.add_column('positions',
        sa.Column('realized_pnl', sa.Numeric(precision=18, scale=4), nullable=False,
                  server_default='0')
    )
    
    # Add index for positions by user and product type
    op.create_index('ix_positions_user_product', 'positions', 
                    ['user_id', 'product_type'], unique=False)


def downgrade() -> None:
    # Drop index for positions by product type
    op.drop_index('ix_positions_user_product', table_name='positions')
    
    # Drop new columns from positions table
    op.drop_column('positions', 'realized_pnl')
    op.drop_column('positions', 'product_type')
    
    # Drop daily_pnl table
    op.drop_index('ix_daily_pnl_user_date', table_name='daily_pnl')
    op.drop_table('daily_pnl')
    
    # Drop user_funds table
    op.drop_index(op.f('ix_user_funds_user_id'), table_name='user_funds')
    op.drop_table('user_funds')


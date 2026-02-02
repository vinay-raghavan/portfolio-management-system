"""add_risk_management_tables

Revision ID: add_risk_tables
Revises: add_enhanced_trading
Create Date: 2025-12-21 14:30:00.000000+00:00

Adds:
- risk_limits table for user-specific trading limits
- daily_risk_metrics table for daily tracking
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_risk_tables'
down_revision: Union[str, None] = 'add_enhanced_trading'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create risk_limits table
    op.create_table('risk_limits',
        sa.Column('id', sa.UUID(as_uuid=False), nullable=False),
        sa.Column('user_id', sa.UUID(as_uuid=False), nullable=False),
        sa.Column('max_position_size', sa.Numeric(precision=18, scale=4), 
                  nullable=False, server_default='100000'),
        sa.Column('max_position_pct', sa.Numeric(precision=5, scale=2), 
                  nullable=False, server_default='20'),
        sa.Column('max_positions', sa.Integer(), nullable=False, server_default='20'),
        sa.Column('max_daily_loss', sa.Numeric(precision=18, scale=4), 
                  nullable=False, server_default='50000'),
        sa.Column('max_daily_loss_pct', sa.Numeric(precision=5, scale=2), 
                  nullable=False, server_default='5'),
        sa.Column('max_order_value', sa.Numeric(precision=18, scale=4), 
                  nullable=False, server_default='50000'),
        sa.Column('max_orders_per_day', sa.Integer(), nullable=False, server_default='50'),
        sa.Column('allow_intraday', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('allow_short_selling', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), 
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), 
                  server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', name='uq_risk_limits_user_id')
    )
    op.create_index(op.f('ix_risk_limits_user_id'), 'risk_limits', ['user_id'], unique=True)

    # Create daily_risk_metrics table
    op.create_table('daily_risk_metrics',
        sa.Column('id', sa.UUID(as_uuid=False), nullable=False),
        sa.Column('user_id', sa.UUID(as_uuid=False), nullable=False),
        sa.Column('date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('orders_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('trades_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('realized_pnl', sa.Numeric(precision=18, scale=4), 
                  nullable=False, server_default='0'),
        sa.Column('unrealized_pnl', sa.Numeric(precision=18, scale=4), 
                  nullable=False, server_default='0'),
        sa.Column('total_traded_value', sa.Numeric(precision=18, scale=4), 
                  nullable=False, server_default='0'),
        sa.Column('daily_loss_limit_breached', sa.Boolean(), 
                  nullable=False, server_default='false'),
        sa.Column('position_limit_breached', sa.Boolean(), 
                  nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), 
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), 
                  server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_daily_risk_metrics_user_date', 'daily_risk_metrics', 
                    ['user_id', 'date'], unique=True)


def downgrade() -> None:
    # Drop daily_risk_metrics table
    op.drop_index('ix_daily_risk_metrics_user_date', table_name='daily_risk_metrics')
    op.drop_table('daily_risk_metrics')
    
    # Drop risk_limits table
    op.drop_index(op.f('ix_risk_limits_user_id'), table_name='risk_limits')
    op.drop_table('risk_limits')


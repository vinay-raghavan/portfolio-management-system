"""add_circuit_breaker_persistence_tables

Revision ID: cb_persistence_001
Revises: add_close_positions_continue
Create Date: 2026-01-06 10:30:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'cb_persistence_001'
down_revision: Union[str, None] = 'add_close_positions_continue'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create circuit_breaker_states table
    op.create_table(
        'circuit_breaker_states',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('strategy_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('user_strategies.id', ondelete='CASCADE'), nullable=False, unique=True, index=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        
        # Circuit breaker status
        sa.Column('is_triggered', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('trigger_reason', sa.Text(), nullable=True),
        sa.Column('triggered_at', sa.DateTime(timezone=True), nullable=True),
        
        # Daily tracking (resets at midnight)
        sa.Column('daily_loss', sa.Numeric(18, 4), nullable=False, server_default='0'),
        sa.Column('daily_profit', sa.Numeric(18, 4), nullable=False, server_default='0'),
        sa.Column('consecutive_losses', sa.Integer(), nullable=False, server_default='0'),
        
        # Overall profit tracking
        sa.Column('overall_profit', sa.Numeric(18, 4), nullable=False, server_default='0'),
        sa.Column('profit_cutoff_triggered', sa.Boolean(), nullable=False, server_default='false'),
        
        # Tracking date for daily reset detection
        sa.Column('tracking_date', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        
        # Sync timestamps
        sa.Column('last_synced_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    
    # Create circuit_breaker_history table
    op.create_table(
        'circuit_breaker_history',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('strategy_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('user_strategies.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        
        # Event details
        sa.Column('event_type', sa.String(20), nullable=False),  # TRIGGERED, RESET, DAILY_RESET
        sa.Column('trigger_reason', sa.Text(), nullable=True),
        
        # State at time of event
        sa.Column('daily_loss', sa.Numeric(18, 4), nullable=False, server_default='0'),
        sa.Column('daily_profit', sa.Numeric(18, 4), nullable=False, server_default='0'),
        sa.Column('consecutive_losses', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('overall_profit', sa.Numeric(18, 4), nullable=False, server_default='0'),
        
        sa.Column('event_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    
    # Create index for history queries
    op.create_index(
        'ix_cb_history_strategy_event',
        'circuit_breaker_history',
        ['strategy_id', 'event_at']
    )


def downgrade() -> None:
    op.drop_index('ix_cb_history_strategy_event', table_name='circuit_breaker_history')
    op.drop_table('circuit_breaker_history')
    op.drop_table('circuit_breaker_states')


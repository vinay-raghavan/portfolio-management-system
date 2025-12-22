"""add signals table

Revision ID: add_signals_table
Revises: add_portfolios
Create Date: 2025-12-22 11:10:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = 'add_signals_table'
down_revision: Union[str, None] = 'add_portfolios'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'signals',
        sa.Column('id', UUID(as_uuid=False), nullable=False),
        sa.Column('user_id', UUID(as_uuid=False), nullable=False),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column(
            'signal_type',
            sa.Enum('BUY', 'SELL', 'HOLD', name='signaltype'),
            nullable=False
        ),
        sa.Column('strength', sa.Numeric(5, 4), nullable=False),
        sa.Column('confidence', sa.Numeric(5, 4), nullable=False),
        sa.Column('strategy_name', sa.String(50), nullable=False),
        sa.Column('timeframe', sa.String(10), nullable=False, server_default='1d'),
        sa.Column('price_at_signal', sa.Numeric(18, 4), nullable=False),
        sa.Column('entry_price', sa.Numeric(18, 4), nullable=True),
        sa.Column('stop_loss', sa.Numeric(18, 4), nullable=True),
        sa.Column('take_profit', sa.Numeric(18, 4), nullable=True),
        sa.Column('risk_reward_ratio', sa.Numeric(6, 2), nullable=True),
        sa.Column('indicators', sa.JSON(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column(
            'status',
            sa.Enum('PENDING', 'ACTIVE', 'EXECUTED', 'CANCELLED', 'EXPIRED', name='signalstatus'),
            nullable=False,
            server_default='PENDING'
        ),
        sa.Column('is_executed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('executed_order_id', UUID(as_uuid=False), nullable=True),
        sa.Column(
            'generated_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text('now()')
        ),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )

    # Create indexes
    op.create_index('ix_signals_user_id', 'signals', ['user_id'])
    op.create_index('ix_signals_symbol', 'signals', ['symbol'])
    op.create_index('ix_signals_status', 'signals', ['status'])
    op.create_index('ix_signals_generated_at', 'signals', ['generated_at'])
    op.create_index('ix_signals_strategy', 'signals', ['strategy_name'])


def downgrade() -> None:
    op.drop_index('ix_signals_strategy', table_name='signals')
    op.drop_index('ix_signals_generated_at', table_name='signals')
    op.drop_index('ix_signals_status', table_name='signals')
    op.drop_index('ix_signals_symbol', table_name='signals')
    op.drop_index('ix_signals_user_id', table_name='signals')
    op.drop_table('signals')
    op.execute('DROP TYPE IF EXISTS signaltype')
    op.execute('DROP TYPE IF EXISTS signalstatus')


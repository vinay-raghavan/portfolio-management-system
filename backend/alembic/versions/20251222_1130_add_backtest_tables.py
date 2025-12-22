"""add backtest tables

Revision ID: add_backtest_tables
Revises: add_signals_table
Create Date: 2025-12-22 11:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = 'add_backtest_tables'
down_revision: Union[str, None] = 'add_signals_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create backtest_results table
    op.create_table(
        'backtest_results',
        sa.Column('id', UUID(as_uuid=False), nullable=False),
        sa.Column('user_id', UUID(as_uuid=False), nullable=False),
        
        # Configuration
        sa.Column('strategy_name', sa.String(50), nullable=False),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('timeframe', sa.String(10), nullable=False, server_default='1d'),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('initial_capital', sa.Numeric(18, 4), nullable=False),
        sa.Column('strategy_params', sa.JSON(), nullable=True),
        
        # Status
        sa.Column('status', sa.String(20), nullable=False, server_default='PENDING'),
        sa.Column('error_message', sa.Text(), nullable=True),
        
        # Performance metrics
        sa.Column('final_capital', sa.Numeric(18, 4), nullable=True),
        sa.Column('total_return', sa.Numeric(10, 4), nullable=True),
        sa.Column('annualized_return', sa.Numeric(10, 4), nullable=True),
        sa.Column('sharpe_ratio', sa.Numeric(8, 4), nullable=True),
        sa.Column('sortino_ratio', sa.Numeric(8, 4), nullable=True),
        sa.Column('max_drawdown', sa.Numeric(8, 4), nullable=True),
        sa.Column('calmar_ratio', sa.Numeric(8, 4), nullable=True),
        
        # Trade statistics
        sa.Column('total_trades', sa.Integer(), nullable=True),
        sa.Column('winning_trades', sa.Integer(), nullable=True),
        sa.Column('losing_trades', sa.Integer(), nullable=True),
        sa.Column('win_rate', sa.Numeric(6, 4), nullable=True),
        sa.Column('profit_factor', sa.Numeric(8, 4), nullable=True),
        sa.Column('avg_win', sa.Numeric(18, 4), nullable=True),
        sa.Column('avg_loss', sa.Numeric(18, 4), nullable=True),
        sa.Column('avg_trade', sa.Numeric(18, 4), nullable=True),
        sa.Column('largest_win', sa.Numeric(18, 4), nullable=True),
        sa.Column('largest_loss', sa.Numeric(18, 4), nullable=True),
        
        # Equity curve data
        sa.Column('equity_curve', sa.JSON(), nullable=True),
        sa.Column('drawdown_curve', sa.JSON(), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    
    # Create indexes for backtest_results
    op.create_index('ix_backtest_results_user_id', 'backtest_results', ['user_id'])
    op.create_index('ix_backtest_results_strategy', 'backtest_results', ['strategy_name'])
    op.create_index('ix_backtest_results_status', 'backtest_results', ['status'])
    op.create_index('ix_backtest_results_created_at', 'backtest_results', ['created_at'])
    
    # Create backtest_trades table
    op.create_table(
        'backtest_trades',
        sa.Column('id', UUID(as_uuid=False), nullable=False),
        sa.Column('backtest_id', UUID(as_uuid=False), nullable=False),
        
        # Trade details
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('side', sa.String(10), nullable=False),
        sa.Column('entry_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('entry_price', sa.Numeric(18, 4), nullable=False),
        sa.Column('exit_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('exit_price', sa.Numeric(18, 4), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=False),
        
        # Trade results
        sa.Column('pnl', sa.Numeric(18, 4), nullable=True),
        sa.Column('pnl_pct', sa.Numeric(10, 4), nullable=True),
        sa.Column('is_winner', sa.Boolean(), nullable=True),
        
        # Additional info
        sa.Column('signal_indicators', sa.JSON(), nullable=True),
        sa.Column('exit_reason', sa.String(50), nullable=True),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['backtest_id'], ['backtest_results.id'], ondelete='CASCADE'),
    )
    
    # Create indexes for backtest_trades
    op.create_index('ix_backtest_trades_backtest_id', 'backtest_trades', ['backtest_id'])
    op.create_index('ix_backtest_trades_entry_date', 'backtest_trades', ['entry_date'])


def downgrade() -> None:
    op.drop_table('backtest_trades')
    op.drop_table('backtest_results')


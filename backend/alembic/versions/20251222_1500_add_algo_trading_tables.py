"""add algo trading tables

Revision ID: add_algo_trading_tables
Revises: add_backtest_tables
Create Date: 2025-12-22 15:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = 'add_algo_trading_tables'
down_revision: Union[str, None] = 'add_backtest_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    op.execute("""
        CREATE TYPE strategystatus AS ENUM (
            'ACTIVE', 'PAUSED', 'DISABLED', 'ERROR', 'KILLED'
        )
    """)
    op.execute("""
        CREATE TYPE scheduletype AS ENUM (
            'INTERVAL', 'CRON', 'MARKET_OPEN', 'MARKET_CLOSE', 'CONTINUOUS'
        )
    """)
    op.execute("""
        CREATE TYPE positionsizingmethod AS ENUM (
            'FIXED_QUANTITY', 'FIXED_AMOUNT', 'PERCENT_OF_PORTFOLIO',
            'RISK_BASED', 'VOLATILITY_ADJUSTED'
        )
    """)
    op.execute("""
        CREATE TYPE executionstatus AS ENUM (
            'RUNNING', 'COMPLETED', 'FAILED', 'NO_SIGNAL', 'RISK_BLOCKED', 'SKIPPED'
        )
    """)

    # Create universes table first (referenced by user_strategies)
    op.create_table(
        'universes',
        sa.Column('id', UUID(as_uuid=False), nullable=False),
        sa.Column('user_id', UUID(as_uuid=False), nullable=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_system', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_dynamic', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('symbols', sa.JSON(), nullable=True),
        sa.Column('filter_criteria', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_universes_user', 'universes', ['user_id'])

    # Create user_strategies table
    op.create_table(
        'user_strategies',
        sa.Column('id', UUID(as_uuid=False), nullable=False),
        sa.Column('user_id', UUID(as_uuid=False), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('strategy_name', sa.String(50), nullable=False),
        sa.Column('status', sa.Enum('ACTIVE', 'PAUSED', 'DISABLED', 'ERROR', 'KILLED',
                  name='strategystatus', create_type=False), nullable=False, server_default='DISABLED'),
        sa.Column('is_paper_trading', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('strategy_params', sa.JSON(), nullable=True),
        # Schedule
        sa.Column('schedule_type', sa.Enum('INTERVAL', 'CRON', 'MARKET_OPEN', 'MARKET_CLOSE', 'CONTINUOUS',
                  name='scheduletype', create_type=False), nullable=False, server_default='MARKET_OPEN'),
        sa.Column('interval_seconds', sa.Integer(), nullable=True),
        sa.Column('cron_expression', sa.String(100), nullable=True),
        sa.Column('timeframe', sa.String(10), nullable=False, server_default='1d'),
        # Universe
        sa.Column('universe_id', UUID(as_uuid=False), nullable=True),
        sa.Column('custom_symbols', sa.JSON(), nullable=True),
        # Position sizing
        sa.Column('position_sizing_method', sa.Enum('FIXED_QUANTITY', 'FIXED_AMOUNT', 'PERCENT_OF_PORTFOLIO',
                  'RISK_BASED', 'VOLATILITY_ADJUSTED', name='positionsizingmethod', create_type=False),
                  nullable=False, server_default='PERCENT_OF_PORTFOLIO'),
        sa.Column('fixed_quantity', sa.Integer(), nullable=True),
        sa.Column('fixed_amount', sa.Numeric(18, 2), nullable=True),
        sa.Column('portfolio_percent', sa.Numeric(5, 2), nullable=False, server_default='5.00'),
        sa.Column('risk_per_trade_percent', sa.Numeric(5, 2), nullable=False, server_default='2.00'),
        sa.Column('max_position_value', sa.Numeric(18, 2), nullable=True),
        # Risk controls
        sa.Column('max_daily_trades', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('max_daily_loss', sa.Numeric(18, 2), nullable=False, server_default='5000.00'),
        sa.Column('max_open_positions', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('cooldown_seconds', sa.Integer(), nullable=False, server_default='60'),
        sa.Column('max_consecutive_losses', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('max_drawdown_percent', sa.Numeric(5, 2), nullable=False, server_default='10.00'),
        # Tracking
        sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_trades', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('winning_trades', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_pnl', sa.Numeric(18, 2), nullable=False, server_default='0'),
        sa.Column('consecutive_losses', sa.Integer(), nullable=False, server_default='0'),
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['universe_id'], ['universes.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_user_strategies_user_status', 'user_strategies', ['user_id', 'status'])
    op.create_index('ix_user_strategies_next_run', 'user_strategies', ['status', 'next_run_at'])

    # Create strategy_executions table
    op.create_table(
        'strategy_executions',
        sa.Column('id', UUID(as_uuid=False), nullable=False),
        sa.Column('strategy_id', UUID(as_uuid=False), nullable=False),
        sa.Column('user_id', UUID(as_uuid=False), nullable=False),
        sa.Column('status', sa.Enum('RUNNING', 'COMPLETED', 'FAILED', 'NO_SIGNAL', 'RISK_BLOCKED', 'SKIPPED',
                  name='executionstatus', create_type=False), nullable=False, server_default='RUNNING'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('symbols_analyzed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('signals_generated', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('orders_placed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('orders_filled', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('orders_rejected', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('signals_data', sa.JSON(), nullable=True),
        sa.Column('orders_data', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('execution_log', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['strategy_id'], ['user_strategies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_strategy_executions_strategy', 'strategy_executions', ['strategy_id', 'started_at'])
    op.create_index('ix_strategy_executions_user', 'strategy_executions', ['user_id', 'started_at'])

    # Create algo_orders table
    op.create_table(
        'algo_orders',
        sa.Column('id', UUID(as_uuid=False), nullable=False),
        sa.Column('execution_id', UUID(as_uuid=False), nullable=False),
        sa.Column('order_id', UUID(as_uuid=False), nullable=False),
        sa.Column('signal_id', UUID(as_uuid=False), nullable=True),
        sa.Column('user_id', UUID(as_uuid=False), nullable=False),
        sa.Column('strategy_id', UUID(as_uuid=False), nullable=False),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('side', sa.String(4), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('order_type', sa.String(20), nullable=False),
        sa.Column('price', sa.Numeric(18, 4), nullable=True),
        sa.Column('signal_type', sa.String(10), nullable=True),
        sa.Column('signal_strength', sa.Numeric(5, 4), nullable=True),
        sa.Column('sizing_method', sa.String(50), nullable=True),
        sa.Column('calculated_quantity', sa.Integer(), nullable=True),
        sa.Column('risk_amount', sa.Numeric(18, 2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['execution_id'], ['strategy_executions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['signal_id'], ['signals.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['strategy_id'], ['user_strategies.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_algo_orders_execution', 'algo_orders', ['execution_id'])
    op.create_index('ix_algo_orders_strategy', 'algo_orders', ['strategy_id', 'created_at'])
    op.create_index('ix_algo_orders_user', 'algo_orders', ['user_id', 'created_at'])

    # Insert predefined system universes
    op.execute("""
        INSERT INTO universes (id, name, description, is_system, symbols) VALUES
        (gen_random_uuid(), 'Nifty 50', 'Top 50 companies by market cap in NSE', true,
         '["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR", "ITC", "KOTAKBANK",
           "LT", "SBIN", "AXISBANK", "BAJFINANCE", "BHARTIARTL", "ASIANPAINT", "HCLTECH",
           "MARUTI", "TITAN", "SUNPHARMA", "ULTRACEMCO", "WIPRO", "NESTLEIND", "POWERGRID",
           "ONGC", "NTPC", "M&M", "TATAMOTORS", "JSWSTEEL", "BAJAJFINSV", "ADANIGREEN", "TATASTEEL",
           "ADANIENT", "TECHM", "HDFCLIFE", "DIVISLAB", "DRREDDY", "COALINDIA", "BRITANNIA",
           "SBILIFE", "GRASIM", "INDUSINDBK", "BPCL", "CIPLA", "EICHERMOT", "HINDALCO",
           "TATACONSUM", "UPL", "APOLLOHOSP", "HEROMOTOCO", "BAJAJ-AUTO", "SHRIRAMFIN"]'),
        (gen_random_uuid(), 'Bank Nifty', 'Major banking stocks', true,
         '["HDFCBANK", "ICICIBANK", "KOTAKBANK", "SBIN", "AXISBANK", "INDUSINDBK", "BANDHANBNK",
           "PNB", "BANKBARODA", "FEDERALBNK", "IDFCFIRSTB", "AUBANK"]'),
        (gen_random_uuid(), 'IT Stocks', 'Major IT companies', true,
         '["TCS", "INFY", "HCLTECH", "WIPRO", "TECHM", "LTIM", "MPHASIS", "COFORGE", "PERSISTENT", "LTTS"]'),
        (gen_random_uuid(), 'Pharma Stocks', 'Major pharmaceutical companies', true,
         '["SUNPHARMA", "DRREDDY", "CIPLA", "DIVISLAB", "BIOCON", "AUROPHARMA", "TORNTPHARM",
           "LUPIN", "ALKEM", "IPCALAB"]')
    """)


def downgrade() -> None:
    op.drop_table('algo_orders')
    op.drop_table('strategy_executions')
    op.drop_table('user_strategies')
    op.drop_table('universes')
    op.execute("DROP TYPE IF EXISTS executionstatus")
    op.execute("DROP TYPE IF EXISTS positionsizingmethod")
    op.execute("DROP TYPE IF EXISTS scheduletype")
    op.execute("DROP TYPE IF EXISTS strategystatus")


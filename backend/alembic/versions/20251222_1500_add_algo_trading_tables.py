"""add algo trading tables

Revision ID: add_algo_trading_tables
Revises: add_backtest_tables
Create Date: 2025-12-22 15:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'add_algo_trading_tables'
down_revision: Union[str, None] = 'add_backtest_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    op.execute("CREATE TYPE strategystatus AS ENUM ('ACTIVE', 'PAUSED', 'DISABLED', 'ERROR', 'KILLED')")
    op.execute("CREATE TYPE scheduletype AS ENUM ('INTERVAL', 'CRON', 'MARKET_OPEN', 'MARKET_CLOSE', 'CONTINUOUS')")
    op.execute("CREATE TYPE positionsizingmethod AS ENUM ('FIXED_QUANTITY', 'FIXED_AMOUNT', 'PERCENT_OF_PORTFOLIO', 'RISK_BASED', 'VOLATILITY_ADJUSTED')")
    op.execute("CREATE TYPE executionstatus AS ENUM ('RUNNING', 'COMPLETED', 'FAILED', 'NO_SIGNAL', 'RISK_BLOCKED', 'SKIPPED')")

    # Create universes table first (referenced by user_strategies)
    op.execute("""
        CREATE TABLE universes (
            id UUID NOT NULL PRIMARY KEY,
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            is_system BOOLEAN NOT NULL DEFAULT false,
            is_dynamic BOOLEAN NOT NULL DEFAULT false,
            symbols JSONB,
            filter_criteria JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.create_index('ix_universes_user', 'universes', ['user_id'])

    # Create user_strategies table using raw SQL to avoid enum creation issues
    op.execute("""
        CREATE TABLE user_strategies (
            id UUID NOT NULL PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            strategy_name VARCHAR(50) NOT NULL,
            status strategystatus NOT NULL DEFAULT 'DISABLED',
            is_paper_trading BOOLEAN NOT NULL DEFAULT true,
            strategy_params JSONB,
            schedule_type scheduletype NOT NULL DEFAULT 'MARKET_OPEN',
            interval_seconds INTEGER,
            cron_expression VARCHAR(100),
            timeframe VARCHAR(10) NOT NULL DEFAULT '1d',
            universe_id UUID REFERENCES universes(id) ON DELETE SET NULL,
            custom_symbols JSONB,
            position_sizing_method positionsizingmethod NOT NULL DEFAULT 'PERCENT_OF_PORTFOLIO',
            fixed_quantity INTEGER,
            fixed_amount NUMERIC(18, 2),
            portfolio_percent NUMERIC(5, 2) NOT NULL DEFAULT 5.00,
            risk_per_trade_percent NUMERIC(5, 2) NOT NULL DEFAULT 2.00,
            max_position_value NUMERIC(18, 2),
            max_daily_trades INTEGER NOT NULL DEFAULT 10,
            max_daily_loss NUMERIC(18, 2) NOT NULL DEFAULT 5000.00,
            max_open_positions INTEGER NOT NULL DEFAULT 5,
            cooldown_seconds INTEGER NOT NULL DEFAULT 60,
            max_consecutive_losses INTEGER NOT NULL DEFAULT 3,
            max_drawdown_percent NUMERIC(5, 2) NOT NULL DEFAULT 10.00,
            last_run_at TIMESTAMPTZ,
            next_run_at TIMESTAMPTZ,
            total_trades INTEGER NOT NULL DEFAULT 0,
            winning_trades INTEGER NOT NULL DEFAULT 0,
            total_pnl NUMERIC(18, 2) NOT NULL DEFAULT 0,
            consecutive_losses INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.create_index('ix_user_strategies_user_status', 'user_strategies', ['user_id', 'status'])
    op.create_index('ix_user_strategies_next_run', 'user_strategies', ['status', 'next_run_at'])

    # Create strategy_executions table
    op.execute("""
        CREATE TABLE strategy_executions (
            id UUID NOT NULL PRIMARY KEY,
            strategy_id UUID NOT NULL REFERENCES user_strategies(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            status executionstatus NOT NULL DEFAULT 'RUNNING',
            started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            completed_at TIMESTAMPTZ,
            duration_ms INTEGER,
            symbols_analyzed INTEGER NOT NULL DEFAULT 0,
            signals_generated INTEGER NOT NULL DEFAULT 0,
            orders_placed INTEGER NOT NULL DEFAULT 0,
            orders_filled INTEGER NOT NULL DEFAULT 0,
            orders_rejected INTEGER NOT NULL DEFAULT 0,
            signals_data JSONB,
            orders_data JSONB,
            error_message TEXT,
            execution_log JSONB
        )
    """)
    op.create_index('ix_strategy_executions_strategy', 'strategy_executions', ['strategy_id', 'started_at'])
    op.create_index('ix_strategy_executions_user', 'strategy_executions', ['user_id', 'started_at'])

    # Create algo_orders table
    op.execute("""
        CREATE TABLE algo_orders (
            id UUID NOT NULL PRIMARY KEY,
            execution_id UUID NOT NULL REFERENCES strategy_executions(id) ON DELETE CASCADE,
            order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
            signal_id UUID REFERENCES signals(id) ON DELETE SET NULL,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            strategy_id UUID NOT NULL REFERENCES user_strategies(id) ON DELETE CASCADE,
            symbol VARCHAR(20) NOT NULL,
            side VARCHAR(4) NOT NULL,
            quantity INTEGER NOT NULL,
            order_type VARCHAR(20) NOT NULL,
            price NUMERIC(18, 4),
            signal_type VARCHAR(10),
            signal_strength NUMERIC(5, 4),
            sizing_method VARCHAR(50),
            calculated_quantity INTEGER,
            risk_amount NUMERIC(18, 2),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
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


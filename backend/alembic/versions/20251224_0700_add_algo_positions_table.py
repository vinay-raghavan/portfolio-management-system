"""add algo positions table for P&L tracking

Revision ID: add_algo_positions_table
Revises: add_algo_trading_tables
Create Date: 2025-12-24 07:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'add_algo_positions_table'
down_revision: Union[str, None] = 'add_algo_trading_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types for positions
    op.execute("CREATE TYPE positionside AS ENUM ('LONG', 'SHORT')")
    op.execute("CREATE TYPE positionstatus AS ENUM ('OPEN', 'CLOSED', 'PARTIAL')")

    # Create algo_positions table for tracking strategy positions and P&L
    op.execute("""
        CREATE TABLE algo_positions (
            id UUID NOT NULL PRIMARY KEY,
            strategy_id UUID NOT NULL REFERENCES user_strategies(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            symbol VARCHAR(20) NOT NULL,
            side positionside NOT NULL DEFAULT 'LONG',
            status positionstatus NOT NULL DEFAULT 'OPEN',
            entry_quantity INTEGER NOT NULL,
            entry_price NUMERIC(18, 4) NOT NULL,
            entry_order_id UUID,
            entry_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            exit_quantity INTEGER,
            exit_price NUMERIC(18, 4),
            exit_order_id UUID,
            exit_at TIMESTAMPTZ,
            remaining_quantity INTEGER NOT NULL,
            realized_pnl NUMERIC(18, 4) NOT NULL DEFAULT 0,
            realized_pnl_percent NUMERIC(10, 4) NOT NULL DEFAULT 0,
            is_winner BOOLEAN,
            stop_loss NUMERIC(18, 4),
            take_profit NUMERIC(18, 4),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # Create indexes
    op.create_index('ix_algo_positions_strategy_status', 'algo_positions', ['strategy_id', 'status'])
    op.create_index('ix_algo_positions_user_symbol', 'algo_positions', ['user_id', 'symbol', 'status'])
    op.create_index('ix_algo_positions_open', 'algo_positions', ['status', 'symbol'])

    # Also fix the algo_orders table - order_id should be nullable since orders are created inline
    op.execute("ALTER TABLE algo_orders ALTER COLUMN order_id DROP NOT NULL")


def downgrade() -> None:
    # Revert algo_orders change
    op.execute("ALTER TABLE algo_orders ALTER COLUMN order_id SET NOT NULL")

    # Drop table and indexes
    op.drop_index('ix_algo_positions_open', table_name='algo_positions')
    op.drop_index('ix_algo_positions_user_symbol', table_name='algo_positions')
    op.drop_index('ix_algo_positions_strategy_status', table_name='algo_positions')
    op.drop_table('algo_positions')

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS positionstatus")
    op.execute("DROP TYPE IF EXISTS positionside")


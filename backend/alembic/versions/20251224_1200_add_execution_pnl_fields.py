"""Add P&L and order status fields to execution tables.

Revision ID: add_execution_pnl_fields
Revises: add_algo_positions_table
Create Date: 2024-12-24 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_execution_pnl_fields'
down_revision: Union[str, None] = 'add_algo_positions_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add P&L fields to strategy_executions table
    op.add_column('strategy_executions', sa.Column('realized_pnl', sa.Numeric(18, 4), nullable=False, server_default='0'))
    op.add_column('strategy_executions', sa.Column('unrealized_pnl', sa.Numeric(18, 4), nullable=False, server_default='0'))
    op.add_column('strategy_executions', sa.Column('total_order_value', sa.Numeric(18, 4), nullable=False, server_default='0'))
    op.add_column('strategy_executions', sa.Column('positions_opened', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('strategy_executions', sa.Column('positions_closed', sa.Integer(), nullable=False, server_default='0'))

    # Add order status and fill fields to algo_orders table
    op.add_column('algo_orders', sa.Column('order_status', sa.String(20), nullable=False, server_default='PENDING'))
    op.add_column('algo_orders', sa.Column('filled_quantity', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('algo_orders', sa.Column('filled_price', sa.Numeric(18, 4), nullable=True))
    op.add_column('algo_orders', sa.Column('order_value', sa.Numeric(18, 4), nullable=False, server_default='0'))
    op.add_column('algo_orders', sa.Column('filled_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # Remove order status and fill fields from algo_orders
    op.drop_column('algo_orders', 'filled_at')
    op.drop_column('algo_orders', 'order_value')
    op.drop_column('algo_orders', 'filled_price')
    op.drop_column('algo_orders', 'filled_quantity')
    op.drop_column('algo_orders', 'order_status')

    # Remove P&L fields from strategy_executions
    op.drop_column('strategy_executions', 'positions_closed')
    op.drop_column('strategy_executions', 'positions_opened')
    op.drop_column('strategy_executions', 'total_order_value')
    op.drop_column('strategy_executions', 'unrealized_pnl')
    op.drop_column('strategy_executions', 'realized_pnl')


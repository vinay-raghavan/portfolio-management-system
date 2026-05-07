"""Add daily P&L tracking columns to user_funds.

Revision ID: 20260330_1000
Revises: 20260324_1001
Create Date: 2026-03-30

These columns support daily portfolio guardrails that trigger based on
intraday loss from day start, not cumulative P&L.
"""

from decimal import Decimal

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "daily_pnl_tracking_001"
down_revision = "strategy_screener_002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add daily P&L tracking columns
    op.add_column(
        "user_funds",
        sa.Column(
            "daily_realized_pnl",
            sa.Numeric(18, 4),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "user_funds",
        sa.Column(
            "daily_start_value",
            sa.Numeric(18, 4),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "user_funds",
        sa.Column(
            "daily_reset_date",
            sa.Date(),
            nullable=True,
        ),
    )

    # Initialize daily_start_value from current portfolio value
    # (cash_balance + margin_used + unrealized_pnl)
    op.execute(
        """
        UPDATE user_funds
        SET daily_start_value = cash_balance + margin_used,
            daily_reset_date = CURRENT_DATE
        """
    )


def downgrade() -> None:
    op.drop_column("user_funds", "daily_reset_date")
    op.drop_column("user_funds", "daily_start_value")
    op.drop_column("user_funds", "daily_realized_pnl")


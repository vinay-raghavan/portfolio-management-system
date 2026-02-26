"""add profit lock stop loss fields

Revision ID: add_profit_lock_fields
Revises: add_trading_time_window
Create Date: 2026-02-26 10:00:00.000000+00:00

Adds profit lock stop loss functionality:
- user_strategies: default_profit_lock_enabled (toggle for new positions)
- algo_positions: profit_lock_enabled, profit_lock_activated, profit_lock_price
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "add_profit_lock_fields"
down_revision: str | None = "add_trading_time_window"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add default profit lock toggle to user_strategies
    # When enabled, positions will use the first profit_booking_rule threshold
    # to lock in profits by moving stop loss to that level
    op.add_column(
        "user_strategies",
        sa.Column(
            "default_profit_lock_enabled",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )

    # Add profit lock fields to algo_positions
    # profit_lock_enabled: whether profit lock is active for this position
    op.add_column(
        "algo_positions",
        sa.Column(
            "profit_lock_enabled",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )

    # profit_lock_activated: whether the profit threshold has been reached
    op.add_column(
        "algo_positions",
        sa.Column(
            "profit_lock_activated",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )

    # profit_lock_price: the price at which profit was locked (effective stop level)
    op.add_column(
        "algo_positions",
        sa.Column(
            "profit_lock_price",
            sa.Numeric(18, 4),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("algo_positions", "profit_lock_price")
    op.drop_column("algo_positions", "profit_lock_activated")
    op.drop_column("algo_positions", "profit_lock_enabled")
    op.drop_column("user_strategies", "default_profit_lock_enabled")

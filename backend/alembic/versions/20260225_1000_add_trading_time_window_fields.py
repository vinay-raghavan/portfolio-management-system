"""add trading time window fields to user_strategies

Revision ID: add_trading_time_window
Revises: add_exit_only_symbols
Create Date: 2026-02-25 10:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "add_trading_time_window"
down_revision: str | None = "add_exit_only_symbols"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add trading time window columns to user_strategies table
    # These allow users to restrict when algo strategies can execute trades

    # Start time of trading window (e.g., 09:45:00)
    op.add_column(
        "user_strategies",
        sa.Column("trading_start_time", sa.Time(), nullable=True),
    )

    # End time of trading window (e.g., 15:15:00)
    op.add_column(
        "user_strategies",
        sa.Column("trading_end_time", sa.Time(), nullable=True),
    )

    # Timezone for trading window (IANA timezone, default Asia/Kolkata)
    op.add_column(
        "user_strategies",
        sa.Column("trading_timezone", sa.String(50), nullable=False, server_default="Asia/Kolkata"),
    )

    # Active trading days (JSON array of weekday indices, Monday=0, Sunday=6)
    op.add_column(
        "user_strategies",
        sa.Column(
            "active_trading_days",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
            server_default="[0, 1, 2, 3, 4]",
        ),
    )


def downgrade() -> None:
    op.drop_column("user_strategies", "active_trading_days")
    op.drop_column("user_strategies", "trading_timezone")
    op.drop_column("user_strategies", "trading_end_time")
    op.drop_column("user_strategies", "trading_start_time")

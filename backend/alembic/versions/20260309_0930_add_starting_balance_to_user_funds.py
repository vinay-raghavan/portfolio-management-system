"""add starting_balance to user_funds

Revision ID: add_starting_balance
Revises: add_signal_direction
Create Date: 2026-03-09

This migration adds a starting_balance column to track the initial balance
when a user's funds account was created. This enables accurate P&L tracking
with the formula: cash_balance = starting_balance + realized_pnl
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "add_starting_balance"
down_revision: str | None = "add_signal_direction"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add starting_balance column with default 100000
    op.add_column(
        "user_funds",
        sa.Column(
            "starting_balance",
            sa.Numeric(precision=18, scale=4),
            nullable=False,
            server_default="100000",
        ),
    )


def downgrade() -> None:
    op.drop_column("user_funds", "starting_balance")


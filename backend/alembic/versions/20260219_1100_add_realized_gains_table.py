"""Add realized_gains table for capital gains tracking.

Revision ID: 2024021911001
Revises: txn_ledger_001
Create Date: 2026-02-19 11:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2024021911001"
down_revision: str | None = "txn_ledger_001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create realized_gains table with indexes."""
    op.create_table(
        "realized_gains",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "portfolio_id",
            UUID(as_uuid=False),
            sa.ForeignKey("portfolios.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Security info
        sa.Column("symbol", sa.String(20), nullable=False),
        # Lot details
        sa.Column("quantity", sa.Numeric(18, 8), nullable=False),
        sa.Column("cost_basis", sa.Numeric(18, 4), nullable=False),
        sa.Column("sale_proceeds", sa.Numeric(18, 4), nullable=False),
        sa.Column("fees", sa.Numeric(18, 4), nullable=False, server_default="0"),
        # Calculated gain/loss
        sa.Column("gain_loss", sa.Numeric(18, 4), nullable=False),
        sa.Column("gain_loss_pct", sa.Numeric(10, 4), nullable=False),
        # Holding period
        sa.Column("purchase_date", sa.DateTime(), nullable=False),
        sa.Column("sale_date", sa.DateTime(), nullable=False),
        sa.Column("holding_days", sa.Integer(), nullable=False),
        sa.Column("is_long_term", sa.Boolean(), nullable=False, server_default="false"),
        # Tax classification
        sa.Column("tax_type", sa.String(20), nullable=False),
        # References
        sa.Column(
            "cost_lot_id",
            UUID(as_uuid=False),
            sa.ForeignKey("cost_lots.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "buy_trade_id",
            UUID(as_uuid=False),
            sa.ForeignKey("trades.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "sell_trade_id",
            UUID(as_uuid=False),
            sa.ForeignKey("trades.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Financial year
        sa.Column("financial_year", sa.String(10), nullable=False),
        # Timestamps
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    # Create indexes for efficient querying
    op.create_index("ix_realized_gains_user_date", "realized_gains", ["user_id", "sale_date"])
    op.create_index("ix_realized_gains_user_fy", "realized_gains", ["user_id", "financial_year"])
    op.create_index("ix_realized_gains_user_symbol", "realized_gains", ["user_id", "symbol"])
    op.create_index("ix_realized_gains_user_tax_type", "realized_gains", ["user_id", "tax_type"])
    op.create_index("ix_realized_gains_portfolio", "realized_gains", ["portfolio_id", "sale_date"])


def downgrade() -> None:
    """Drop realized_gains table and indexes."""
    op.drop_index("ix_realized_gains_portfolio", table_name="realized_gains")
    op.drop_index("ix_realized_gains_user_tax_type", table_name="realized_gains")
    op.drop_index("ix_realized_gains_user_symbol", table_name="realized_gains")
    op.drop_index("ix_realized_gains_user_fy", table_name="realized_gains")
    op.drop_index("ix_realized_gains_user_date", table_name="realized_gains")
    op.drop_table("realized_gains")

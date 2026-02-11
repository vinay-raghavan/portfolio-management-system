"""Add realized_pnl and unrealized_pnl columns to user_funds table.

Revision ID: add_pnl_columns_user_funds
Revises: 20260203_1000_add_product_type_to_strategies
Create Date: 2026-02-05 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "add_pnl_columns_user_funds"
down_revision = "20260203_1000_add_product_type_to_strategies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add realized_pnl column with default 0
    op.add_column(
        "user_funds",
        sa.Column(
            "realized_pnl",
            sa.Numeric(precision=18, scale=4),
            nullable=False,
            server_default="0",
        ),
    )

    # Add unrealized_pnl column with default 0
    op.add_column(
        "user_funds",
        sa.Column(
            "unrealized_pnl",
            sa.Numeric(precision=18, scale=4),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("user_funds", "unrealized_pnl")
    op.drop_column("user_funds", "realized_pnl")


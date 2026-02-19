"""Add transaction_ledger table

Revision ID: txn_ledger_001
Revises: a1b2c3d4e5f6
Create Date: 2026-02-19 10:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision = "txn_ledger_001"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create transaction_ledger table
    op.create_table(
        "transaction_ledger",
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
            sa.ForeignKey("portfolios.id", ondelete="CASCADE"),
            nullable=True,
        ),
        # Transaction details
        sa.Column("transaction_type", sa.String(20), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        # Running balances
        sa.Column("running_cash_balance", sa.Numeric(18, 4), nullable=False),
        sa.Column("running_margin_used", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("running_total_balance", sa.Numeric(18, 4), nullable=False),
        # Reference fields
        sa.Column("reference_type", sa.String(50), nullable=True),
        sa.Column("reference_id", UUID(as_uuid=False), nullable=True),
        # Descriptive info
        sa.Column("symbol", sa.String(20), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("extra_data", sa.JSON(), nullable=True),
        # Timestamps
        sa.Column("transaction_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Create indexes for efficient querying
    op.create_index(
        "ix_txn_ledger_user_date", "transaction_ledger", ["user_id", "transaction_date"]
    )
    op.create_index(
        "ix_txn_ledger_user_type", "transaction_ledger", ["user_id", "transaction_type"]
    )
    op.create_index("ix_txn_ledger_user_symbol", "transaction_ledger", ["user_id", "symbol"])
    op.create_index(
        "ix_txn_ledger_portfolio_date",
        "transaction_ledger",
        ["portfolio_id", "transaction_date"],
    )
    op.create_index(
        "ix_txn_ledger_reference",
        "transaction_ledger",
        ["reference_type", "reference_id"],
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_txn_ledger_reference", table_name="transaction_ledger")
    op.drop_index("ix_txn_ledger_portfolio_date", table_name="transaction_ledger")
    op.drop_index("ix_txn_ledger_user_symbol", table_name="transaction_ledger")
    op.drop_index("ix_txn_ledger_user_type", table_name="transaction_ledger")
    op.drop_index("ix_txn_ledger_user_date", table_name="transaction_ledger")

    # Drop table
    op.drop_table("transaction_ledger")

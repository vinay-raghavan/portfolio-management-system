"""add slb_positions table

Revision ID: add_slb_positions
Revises: add_position_product_type
Create Date: 2026-03-09

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "add_slb_positions"
down_revision: str | None = "add_position_product_type"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create SLB position status enum
    slb_status_enum = postgresql.ENUM(
        "ACTIVE", "RETURNED", "DEFAULTED", name="slbpositionstatus", create_type=False
    )

    # Create enum type if it doesn't exist
    op.execute("CREATE TYPE slbpositionstatus AS ENUM ('ACTIVE', 'RETURNED', 'DEFAULTED')")

    # Create slb_positions table
    op.create_table(
        "slb_positions",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "algo_position_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("algo_positions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column(
            "borrow_date", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("return_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("borrow_rate", sa.Numeric(10, 4), nullable=False),
        sa.Column("daily_fee", sa.Numeric(18, 4), nullable=False),
        sa.Column("total_fee_accrued", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("status", slb_status_enum, nullable=False, server_default="ACTIVE"),
        sa.Column("broker_slb_id", sa.String(100), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )

    # Create indexes
    op.create_index("ix_slb_positions_user", "slb_positions", ["user_id"])
    op.create_index("ix_slb_positions_symbol", "slb_positions", ["symbol"])
    op.create_index("ix_slb_positions_status", "slb_positions", ["status"])
    op.create_index("ix_slb_positions_return_date", "slb_positions", ["return_date"])

    # Add SLB to product type enum if not exists
    op.execute("ALTER TYPE strategyproducttype ADD VALUE IF NOT EXISTS 'SLB'")


def downgrade() -> None:
    op.drop_index("ix_slb_positions_return_date", table_name="slb_positions")
    op.drop_index("ix_slb_positions_status", table_name="slb_positions")
    op.drop_index("ix_slb_positions_symbol", table_name="slb_positions")
    op.drop_index("ix_slb_positions_user", table_name="slb_positions")
    op.drop_table("slb_positions")
    op.execute("DROP TYPE slbpositionstatus")
    # Note: Cannot remove enum values in PostgreSQL, SLB will remain in strategyproducttype

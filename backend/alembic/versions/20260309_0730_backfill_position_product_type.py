"""backfill position product_type from strategy

Revision ID: backfill_position_product_type
Revises: add_slb_positions
Create Date: 2026-03-09

This migration backfills the product_type column for existing positions
that were opened before the product_type column was added.

It copies the product_type from the linked user_strategy to ensure
existing INTRADAY positions are properly identified for auto square-off.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "backfill_position_product_type"
down_revision: str | None = "add_slb_positions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Backfill product_type for existing positions from their strategy
    # This ensures existing INTRADAY positions are picked up by auto square-off
    op.execute(
        """
        UPDATE algo_positions ap
        SET product_type = us.product_type
        FROM user_strategies us
        WHERE ap.strategy_id = us.id
          AND ap.product_type IS NULL
        """
    )


def downgrade() -> None:
    # Set product_type back to NULL for positions that were backfilled
    # (We can't know which ones were originally NULL vs set by new code,
    # so this is a best-effort rollback)
    pass

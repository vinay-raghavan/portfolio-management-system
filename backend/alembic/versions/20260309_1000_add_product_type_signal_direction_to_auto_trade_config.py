"""add product_type and signal_direction to auto_trade_configs

Revision ID: add_auto_trade_config_fields
Revises: add_starting_balance
Create Date: 2026-03-09

This migration adds product_type and signal_direction columns to auto_trade_configs
table so that strategies created from auto-trade have the correct trading settings.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "add_auto_trade_config_fields"
down_revision: str | None = "add_starting_balance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add product_type column (reuse existing enum from user_strategies)
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'auto_trade_configs' AND column_name = 'product_type'
            ) THEN
                ALTER TABLE auto_trade_configs
                ADD COLUMN product_type strategyproducttype NOT NULL DEFAULT 'INTRADAY';
            END IF;
        END $$;
        """
    )

    # Add signal_direction column (reuse existing enum from user_strategies)
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'auto_trade_configs' AND column_name = 'signal_direction'
            ) THEN
                ALTER TABLE auto_trade_configs 
                ADD COLUMN signal_direction signaldirection NOT NULL DEFAULT 'LONG';
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.drop_column("auto_trade_configs", "signal_direction")
    op.drop_column("auto_trade_configs", "product_type")


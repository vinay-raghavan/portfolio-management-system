"""Cleanup duplicate auto_trade_configs

Revision ID: 20260324_1001
Revises: 20260324_1000
Create Date: 2026-03-24 10:01:00.000000

This migration cleans up duplicate auto_trade_configs per screener.
Keeps the most recently created config for each user+screener combination.
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260324_1001"
down_revision = "20260324_1000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Delete duplicate auto_trade_configs, keeping only the most recent one
    # for each user_id + saved_screener_id combination
    op.execute("""
        DELETE FROM auto_trade_configs
        WHERE id IN (
            SELECT id FROM (
                SELECT 
                    id,
                    ROW_NUMBER() OVER (
                        PARTITION BY user_id, saved_screener_id 
                        ORDER BY created_at DESC
                    ) as rn
                FROM auto_trade_configs
                WHERE saved_screener_id IS NOT NULL
            ) ranked
            WHERE rn > 1
        )
    """)


def downgrade() -> None:
    # Cannot restore deleted duplicates
    pass


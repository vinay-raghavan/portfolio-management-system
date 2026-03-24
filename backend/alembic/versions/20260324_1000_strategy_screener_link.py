"""Add strategy-screener linking fields

Revision ID: 20260324_1000
Revises: 20260316_1300_add_portfolio_safety_config
Create Date: 2026-03-24 10:00:00.000000

This migration:
1. Adds linked_screener_id to user_strategies (FK to custom_screeners)
2. Adds sync_from_screener boolean flag to user_strategies
3. Adds unique constraint on auto_trade_configs.saved_screener_id per user
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "strategy_screener_001"
down_revision = "portfolio_safety_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add linked_screener_id to user_strategies
    op.add_column(
        "user_strategies",
        sa.Column(
            "linked_screener_id",
            sa.UUID(),
            nullable=True,
            comment="Links strategy to a custom screener for settings sync",
        ),
    )
    
    # Add sync_from_screener flag
    op.add_column(
        "user_strategies",
        sa.Column(
            "sync_from_screener",
            sa.Boolean(),
            nullable=False,
            server_default="true",
            comment="If true, screener master settings override on each auto-trade run",
        ),
    )
    
    # Add foreign key constraint
    op.create_foreign_key(
        "fk_user_strategies_linked_screener",
        "user_strategies",
        "custom_screeners",
        ["linked_screener_id"],
        ["id"],
        ondelete="SET NULL",
    )
    
    # Add index for faster lookups
    op.create_index(
        "ix_user_strategies_linked_screener",
        "user_strategies",
        ["linked_screener_id"],
    )
    
    # Add unique constraint on auto_trade_configs per user+screener
    # First, we need to handle existing duplicates - keep the most recent one
    # This is done in a separate data migration step
    
    # Create partial unique index (only when saved_screener_id is not null)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ix_auto_trade_configs_user_screener_unique 
        ON auto_trade_configs (user_id, saved_screener_id) 
        WHERE saved_screener_id IS NOT NULL
    """)


def downgrade() -> None:
    # Remove unique index
    op.execute("DROP INDEX IF EXISTS ix_auto_trade_configs_user_screener_unique")
    
    # Remove index
    op.drop_index("ix_user_strategies_linked_screener", table_name="user_strategies")
    
    # Remove foreign key
    op.drop_constraint(
        "fk_user_strategies_linked_screener",
        "user_strategies",
        type_="foreignkey",
    )
    
    # Remove columns
    op.drop_column("user_strategies", "sync_from_screener")
    op.drop_column("user_strategies", "linked_screener_id")


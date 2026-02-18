"""Add sort_order to watchlists and watchlist_items

Revision ID: a1b2c3d4e5f6
Revises: research_provider_001
Create Date: 2026-02-17 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "research_provider_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add sort_order column to watchlists table
    op.add_column(
        "watchlists",
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0")
    )
    # Add sort_order column to watchlist_items table
    op.add_column(
        "watchlist_items",
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0")
    )


def downgrade() -> None:
    op.drop_column("watchlist_items", "sort_order")
    op.drop_column("watchlists", "sort_order")


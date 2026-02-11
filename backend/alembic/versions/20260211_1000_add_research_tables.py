"""Add research module tables.

Revision ID: research_001
Revises: add_pnl_columns_user_funds
Create Date: 2026-02-11 10:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "research_001"
down_revision: str | None = "add_pnl_columns_user_funds"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create research module tables."""
    # 1. research_notes - User research notes for stocks
    op.create_table(
        "research_notes",
        sa.Column("id", UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", UUID(as_uuid=False), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("rating", sa.String(length=20), nullable=True),
        sa.Column("target_price", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("tags", JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_research_notes_user", "research_notes", ["user_id"], unique=False)
    op.create_index("ix_research_notes_symbol", "research_notes", ["symbol"], unique=False)
    op.create_index(
        "ix_research_notes_user_symbol", "research_notes", ["user_id", "symbol"], unique=False
    )

    # 2. daily_digests - Daily market intelligence digest
    op.create_table(
        "daily_digests",
        sa.Column("id", UUID(as_uuid=False), nullable=False),
        sa.Column("digest_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("market_summary", JSONB(), nullable=True),
        sa.Column("top_gainers", JSONB(), nullable=True),
        sa.Column("top_losers", JSONB(), nullable=True),
        sa.Column("sector_performance", JSONB(), nullable=True),
        sa.Column("volume_leaders", JSONB(), nullable=True),
        sa.Column("breakout_candidates", JSONB(), nullable=True),
        sa.Column("news_highlights", JSONB(), nullable=True),
        sa.Column("market_sentiment", sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("digest_date", name="uq_daily_digests_date"),
    )
    op.create_index("ix_daily_digests_date", "daily_digests", ["digest_date"], unique=False)


def downgrade() -> None:
    """Drop research module tables."""
    op.drop_index("ix_daily_digests_date", table_name="daily_digests")
    op.drop_table("daily_digests")

    op.drop_index("ix_research_notes_user_symbol", table_name="research_notes")
    op.drop_index("ix_research_notes_symbol", table_name="research_notes")
    op.drop_index("ix_research_notes_user", table_name="research_notes")
    op.drop_table("research_notes")

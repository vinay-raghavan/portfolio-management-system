"""Add multi-factor scoring fields to daily_recommendations.

Revision ID: 20260223_1200
Revises: 20260223_1100_add_auto_trade_config_tables
Create Date: 2026-02-23 12:00:00.000000

Section 2.6.11: Multi-Factor Integration
Adds technical, fundamental, and sentiment scoring fields for enhanced
recommendation analysis and auto-trade decision making.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260223_1200"
down_revision = "auto_trade_config_001"  # Points to 20260223_1100_add_auto_trade_config_tables.py
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add multi-factor scoring columns to daily_recommendations."""
    # Add multi-factor scoring fields
    op.add_column(
        "daily_recommendations",
        sa.Column("technical_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "daily_recommendations",
        sa.Column("fundamental_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "daily_recommendations",
        sa.Column("sentiment_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "daily_recommendations",
        sa.Column("combined_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "daily_recommendations",
        sa.Column("signal_direction", sa.String(10), nullable=True),
    )
    op.add_column(
        "daily_recommendations",
        sa.Column("confidence_level", sa.String(10), nullable=True),
    )
    op.add_column(
        "daily_recommendations",
        sa.Column("recommended_strategy", sa.String(50), nullable=True),
    )
    op.add_column(
        "daily_recommendations",
        sa.Column("position_size_multiplier", sa.Float(), nullable=True),
    )
    op.add_column(
        "daily_recommendations",
        sa.Column("skip_reason", sa.String(200), nullable=True),
    )


def downgrade() -> None:
    """Remove multi-factor scoring columns."""
    op.drop_column("daily_recommendations", "skip_reason")
    op.drop_column("daily_recommendations", "position_size_multiplier")
    op.drop_column("daily_recommendations", "recommended_strategy")
    op.drop_column("daily_recommendations", "confidence_level")
    op.drop_column("daily_recommendations", "signal_direction")
    op.drop_column("daily_recommendations", "combined_score")
    op.drop_column("daily_recommendations", "sentiment_score")
    op.drop_column("daily_recommendations", "fundamental_score")
    op.drop_column("daily_recommendations", "technical_score")


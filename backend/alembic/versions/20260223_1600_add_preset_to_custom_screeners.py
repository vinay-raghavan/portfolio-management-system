"""Add preset and strictness fields to custom_screeners table.

Revision ID: add_preset_to_screeners
Revises: add_run_time_config
Create Date: 2026-02-23 16:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "add_preset_to_screeners"
down_revision: Union[str, None] = "add_run_time_config"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add preset and strictness columns to custom_screeners.
    
    This allows saving preset screeners (minervini, momentum, etc.)
    in addition to custom screeners with manual filters.
    """
    # Add preset column to store preset screener name
    op.add_column(
        "custom_screeners",
        sa.Column(
            "preset",
            sa.String(50),
            nullable=True,
            comment="Preset screener name (minervini, momentum, breakout, etc.)",
        ),
    )
    
    # Add strictness level for preset screeners
    op.add_column(
        "custom_screeners",
        sa.Column(
            "strictness",
            sa.String(20),
            nullable=True,
            server_default="moderate",
            comment="Strictness level for preset screeners (strict, moderate, relaxed, exploratory)",
        ),
    )
    
    # Make filters column nullable (can be empty when preset is set)
    op.alter_column(
        "custom_screeners",
        "filters",
        existing_type=sa.JSON(),
        nullable=True,
    )
    
    # Add index for preset queries
    op.create_index(
        "ix_custom_screeners_preset",
        "custom_screeners",
        ["preset"],
        unique=False,
    )


def downgrade() -> None:
    """Remove preset and strictness columns from custom_screeners."""
    op.drop_index("ix_custom_screeners_preset", table_name="custom_screeners")
    
    # Revert filters to non-nullable (set empty dict for null values first)
    op.execute("UPDATE custom_screeners SET filters = '{}' WHERE filters IS NULL")
    op.alter_column(
        "custom_screeners",
        "filters",
        existing_type=sa.JSON(),
        nullable=False,
    )
    
    op.drop_column("custom_screeners", "strictness")
    op.drop_column("custom_screeners", "preset")


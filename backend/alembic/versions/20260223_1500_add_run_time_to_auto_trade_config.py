"""Add run_time to auto_trade_configs table.

Revision ID: add_run_time_config
Revises: add_multi_factor_fields
Create Date: 2026-02-23 15:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "add_run_time_config"
down_revision: Union[str, None] = "add_multi_factor_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add run_time column to auto_trade_configs."""
    op.add_column(
        "auto_trade_configs",
        sa.Column(
            "run_time",
            sa.String(5),
            nullable=True,
            server_default="09:20",
            comment="Scheduled run time in HH:MM format (e.g., 09:20 for 9:20 AM IST)",
        ),
    )


def downgrade() -> None:
    """Remove run_time column from auto_trade_configs."""
    op.drop_column("auto_trade_configs", "run_time")


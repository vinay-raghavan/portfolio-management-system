"""add signal_direction to user_strategies

Revision ID: add_signal_direction
Revises: backfill_position_product_type
Create Date: 2026-03-09

Adds signal_direction column to user_strategies table to allow users
to specify whether the strategy should generate LONG, SHORT, or BOTH signals.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "add_signal_direction"
down_revision: str | None = "backfill_position_product_type"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create signal direction enum
    op.execute("CREATE TYPE signaldirection AS ENUM ('LONG', 'SHORT', 'BOTH')")

    # Add signal_direction column with default LONG
    op.add_column(
        "user_strategies",
        sa.Column(
            "signal_direction",
            sa.Enum("LONG", "SHORT", "BOTH", name="signaldirection", create_type=False),
            nullable=False,
            server_default="LONG",
        ),
    )


def downgrade() -> None:
    op.drop_column("user_strategies", "signal_direction")
    op.execute("DROP TYPE signaldirection")

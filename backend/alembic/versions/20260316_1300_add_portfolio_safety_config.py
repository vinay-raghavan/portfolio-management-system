"""add portfolio safety configuration table

Revision ID: portfolio_safety_001
Revises: add_auto_trade_config_fields
Create Date: 2026-03-16

Adds a user-level portfolio safety guardrail config used by trading-engine
to auto-stop trading when loss limits are breached.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "portfolio_safety_001"
down_revision: str | None = "add_auto_trade_config_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "portfolio_safety_configs",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "threshold_type",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'PERCENT'"),
        ),
        sa.Column(
            "threshold_value",
            sa.Numeric(18, 4),
            nullable=False,
            server_default=sa.text("5.00"),
        ),
        sa.Column(
            "action_mode",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'PAUSE_ONLY'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("portfolio_safety_configs")

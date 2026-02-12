"""Add screener_alerts table.

Revision ID: screener_alerts_001
Revises: research_001
Create Date: 2026-02-11 11:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "screener_alerts_001"
down_revision: str | None = "research_001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create screener_alerts table."""
    op.create_table(
        "screener_alerts",
        sa.Column("id", UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", UUID(as_uuid=False), nullable=False),
        sa.Column("custom_screener_id", UUID(as_uuid=False), nullable=True),
        sa.Column("preset", sa.String(length=50), nullable=True),
        sa.Column("universe", sa.String(length=50), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("alert_on_new_symbols", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("alert_on_removed_symbols", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("min_score_threshold", sa.Float(), nullable=True),
        sa.Column("target_symbol", sa.String(length=20), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_symbols", JSONB(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["custom_screener_id"], ["custom_screeners.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_screener_alerts_user", "screener_alerts", ["user_id"], unique=False)
    op.create_index("ix_screener_alerts_enabled", "screener_alerts", ["enabled"], unique=False)


def downgrade() -> None:
    """Drop screener_alerts table."""
    op.drop_index("ix_screener_alerts_enabled", table_name="screener_alerts")
    op.drop_index("ix_screener_alerts_user", table_name="screener_alerts")
    op.drop_table("screener_alerts")


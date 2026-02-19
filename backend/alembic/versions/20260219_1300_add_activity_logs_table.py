"""Add activity_logs table.

Revision ID: 20260219_1300
Revises: 20260219_1200
Create Date: 2026-02-19 13:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260219_1300"
down_revision: str = "20260219_1200"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create activity_logs table."""
    op.create_table(
        "activity_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        # Activity details
        sa.Column("activity_type", sa.String(50), nullable=False),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("title", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        # Entity reference
        sa.Column("entity_type", sa.String(50), nullable=True),
        sa.Column("entity_id", sa.UUID(), nullable=True),
        # Additional context
        sa.Column("extra_data", sa.JSON(), nullable=True),
        # Severity/importance
        sa.Column("severity", sa.String(20), nullable=False, server_default="info"),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false"),
        # Client info
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index(
        "ix_activity_logs_user_id",
        "activity_logs",
        ["user_id"],
    )
    op.create_index(
        "ix_activity_logs_user_created",
        "activity_logs",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_activity_logs_user_type",
        "activity_logs",
        ["user_id", "activity_type"],
    )
    op.create_index(
        "ix_activity_logs_user_category",
        "activity_logs",
        ["user_id", "category"],
    )
    op.create_index(
        "ix_activity_logs_entity",
        "activity_logs",
        ["entity_type", "entity_id"],
    )
    op.create_index(
        "ix_activity_logs_user_unread",
        "activity_logs",
        ["user_id", "is_read"],
    )


def downgrade() -> None:
    """Drop activity_logs table."""
    op.drop_index("ix_activity_logs_user_unread", table_name="activity_logs")
    op.drop_index("ix_activity_logs_entity", table_name="activity_logs")
    op.drop_index("ix_activity_logs_user_category", table_name="activity_logs")
    op.drop_index("ix_activity_logs_user_type", table_name="activity_logs")
    op.drop_index("ix_activity_logs_user_created", table_name="activity_logs")
    op.drop_index("ix_activity_logs_user_id", table_name="activity_logs")
    op.drop_table("activity_logs")

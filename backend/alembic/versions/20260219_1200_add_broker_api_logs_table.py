"""Add broker_api_logs table for API call tracking.

Revision ID: 2024021912001
Revises: 2024021911001
Create Date: 2026-02-19 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2024021912001"
down_revision: str | None = "2024021911001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create broker_api_logs table with indexes."""
    op.create_table(
        "broker_api_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Broker info
        sa.Column("broker_type", sa.String(50), nullable=False),
        # Request details
        sa.Column("endpoint", sa.String(500), nullable=False),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("request_data", sa.JSON(), nullable=True),
        # Response details
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("response_data", sa.JSON(), nullable=True),
        sa.Column("is_success", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("error_message", sa.Text(), nullable=True),
        # Performance
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        # Context
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("reference_type", sa.String(50), nullable=True),
        sa.Column("reference_id", sa.String(36), nullable=True),
        # Timestamps
        sa.Column("request_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("response_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Create indexes
    op.create_index("ix_broker_api_logs_user_date", "broker_api_logs", ["user_id", "request_at"])
    op.create_index(
        "ix_broker_api_logs_broker_action", "broker_api_logs", ["broker_type", "action"]
    )
    op.create_index(
        "ix_broker_api_logs_reference", "broker_api_logs", ["reference_type", "reference_id"]
    )


def downgrade() -> None:
    """Drop broker_api_logs table and indexes."""
    op.drop_index("ix_broker_api_logs_reference", table_name="broker_api_logs")
    op.drop_index("ix_broker_api_logs_broker_action", table_name="broker_api_logs")
    op.drop_index("ix_broker_api_logs_user_date", table_name="broker_api_logs")
    op.drop_table("broker_api_logs")

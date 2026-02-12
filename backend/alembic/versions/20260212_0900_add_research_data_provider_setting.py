"""Add research_data_provider column to user_settings.

Revision ID: research_provider_001
Revises: screener_alerts_001
Create Date: 2026-02-12 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "research_provider_001"
down_revision: str | None = "screener_alerts_001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add research_data_provider column to user_settings."""
    op.add_column(
        "user_settings",
        sa.Column(
            "research_data_provider",
            sa.String(length=50),
            nullable=False,
            server_default="yahoo",
        ),
    )


def downgrade() -> None:
    """Remove research_data_provider column from user_settings."""
    op.drop_column("user_settings", "research_data_provider")


"""add_broker_api_logs_user_broker_action_index

Revision ID: ad231632e600
Revises: 20260219_1300
Create Date: 2026-02-20 04:20:09.215566+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ad231632e600'
down_revision: Union[str, None] = '20260219_1300'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_broker_api_logs_user_broker_action",
        "broker_api_logs",
        ["user_id", "broker_type", "action"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_broker_api_logs_user_broker_action", table_name="broker_api_logs")


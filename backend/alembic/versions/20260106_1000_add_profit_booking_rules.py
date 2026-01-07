"""Add profit_booking_rules to Position model.

Revision ID: add_profit_booking_rules
Revises: add_close_positions_continue
Create Date: 2026-01-06 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_profit_booking_rules'
down_revision: Union[str, None] = 'add_close_positions_continue'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add profit_booking_rules column to positions table
    op.add_column('positions', sa.Column('profit_booking_rules', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    # Add profit_booking_rules column to algo_positions table
    op.add_column('algo_positions', sa.Column('profit_booking_rules', postgresql.JSON(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    # Remove profit_booking_rules column from positions table
    op.drop_column('positions', 'profit_booking_rules')
    # Remove profit_booking_rules column from algo_positions table
    op.drop_column('algo_positions', 'profit_booking_rules')


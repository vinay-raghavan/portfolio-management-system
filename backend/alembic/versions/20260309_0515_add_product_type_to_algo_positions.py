"""add product_type to algo_positions

Revision ID: add_position_product_type
Revises: add_profit_lock_fields
Create Date: 2026-03-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_position_product_type'
down_revision: Union[str, None] = 'add_profit_lock_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add product_type column to algo_positions table
    # This stores the product type at the time the position was opened
    # to ensure correct margin handling when the position is closed
    # (even if the strategy's product_type is changed later)
    op.add_column(
        'algo_positions',
        sa.Column(
            'product_type',
            postgresql.ENUM('DELIVERY', 'INTRADAY', 'MARGIN', name='strategyproducttype', create_type=False),
            nullable=True,
        )
    )


def downgrade() -> None:
    op.drop_column('algo_positions', 'product_type')


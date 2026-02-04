"""Add product_type field to user_strategies for CNC/MIS/MTF support.

Revision ID: add_product_type_strategies
Revises: screener_001
Create Date: 2026-02-03 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'add_product_type_strategies'
down_revision: Union[str, None] = 'screener_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add product_type enum and column to user_strategies."""
    # Create the enum type for strategy product type
    op.execute("""
        CREATE TYPE strategyproducttype AS ENUM (
            'DELIVERY',
            'INTRADAY',
            'MARGIN'
        )
    """)

    # Add product_type column to user_strategies table
    # Default to DELIVERY (CNC) which is the safest option
    op.add_column(
        'user_strategies',
        sa.Column(
            'product_type',
            sa.Enum('DELIVERY', 'INTRADAY', 'MARGIN',
                    name='strategyproducttype', create_type=False),
            nullable=False,
            server_default='DELIVERY'
        )
    )


def downgrade() -> None:
    """Remove product_type column and enum."""
    op.drop_column('user_strategies', 'product_type')
    op.execute("DROP TYPE strategyproducttype")


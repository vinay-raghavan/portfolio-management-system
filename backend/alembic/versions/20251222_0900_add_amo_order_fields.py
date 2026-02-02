"""Add AMO (After Market Order) fields to orders table

Revision ID: add_amo_fields
Revises: 976587252025
Create Date: 2025-12-22 09:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'add_amo_fields'
down_revision: Union[str, None] = '976587252025'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add AMO-related columns to orders table
    op.add_column('orders', sa.Column(
        'is_amo',
        sa.Boolean(),
        nullable=False,
        server_default=sa.text('false')
    ))
    op.add_column('orders', sa.Column(
        'scheduled_for',
        sa.DateTime(timezone=True),
        nullable=True
    ))
    
    # Create index for efficient AMO order queries
    op.create_index(
        'ix_orders_amo_pending',
        'orders',
        ['status', 'is_amo'],
        postgresql_where=sa.text("status = 'AMO_PENDING'")
    )


def downgrade() -> None:
    op.drop_index('ix_orders_amo_pending', table_name='orders')
    op.drop_column('orders', 'scheduled_for')
    op.drop_column('orders', 'is_amo')


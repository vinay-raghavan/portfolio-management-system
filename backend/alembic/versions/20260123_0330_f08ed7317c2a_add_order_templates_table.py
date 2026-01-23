"""add order templates table

Revision ID: f08ed7317c2a
Revises: strategy_risk_001
Create Date: 2026-01-23 03:30:38.767644+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f08ed7317c2a'
down_revision: Union[str, None] = 'strategy_risk_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create order_templates table for quick repeat orders."""
    op.create_table('order_templates',
    sa.Column('id', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('user_id', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('symbol', sa.String(length=20), nullable=False),
    sa.Column('side', sa.String(length=4), nullable=False),
    sa.Column('order_type', sa.String(length=20), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=True),
    sa.Column('quantity_pct', sa.Numeric(precision=5, scale=2), nullable=True),
    sa.Column('stop_loss_pct', sa.Numeric(precision=5, scale=2), nullable=True),
    sa.Column('take_profit_pct', sa.Numeric(precision=5, scale=2), nullable=True),
    sa.Column('is_favorite', sa.Boolean(), nullable=False),
    sa.Column('use_count', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_order_templates_user', 'order_templates', ['user_id'], unique=False)
    op.create_index('ix_order_templates_user_favorite', 'order_templates', ['user_id', 'is_favorite'], unique=False)


def downgrade() -> None:
    """Drop order_templates table."""
    op.drop_index('ix_order_templates_user_favorite', table_name='order_templates')
    op.drop_index('ix_order_templates_user', table_name='order_templates')
    op.drop_table('order_templates')


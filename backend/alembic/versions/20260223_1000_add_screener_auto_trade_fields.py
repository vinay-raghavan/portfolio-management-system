"""add screener auto-trade fields

Revision ID: screener_auto_trade_001
Revises: 228fbbcc60c3
Create Date: 2026-02-23 10:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = 'screener_auto_trade_001'
down_revision: Union[str, None] = '228fbbcc60c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add auto-trade integration fields to custom_screeners table."""
    # Add auto-trade enabled flag
    op.add_column(
        'custom_screeners',
        sa.Column('is_auto_trade_enabled', sa.Boolean(), nullable=False, server_default='false')
    )

    # Add scheduling fields
    op.add_column(
        'custom_screeners',
        sa.Column('run_frequency', sa.String(length=20), nullable=False, server_default='manual')
    )
    op.add_column(
        'custom_screeners',
        sa.Column('run_time', sa.Time(), nullable=True)
    )

    # Add run tracking fields
    op.add_column(
        'custom_screeners',
        sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        'custom_screeners',
        sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=True)
    )

    # Add strategy inference field
    op.add_column(
        'custom_screeners',
        sa.Column('inferred_strategy_type', sa.String(length=50), nullable=True)
    )

    # Add strategy template link for auto-trade execution params
    op.add_column(
        'custom_screeners',
        sa.Column(
            'strategy_template_id',
            UUID(as_uuid=False),
            sa.ForeignKey('user_strategies.id', ondelete='SET NULL'),
            nullable=True
        )
    )

    # Add index for auto-trade queries
    op.create_index(
        'ix_custom_screeners_auto_trade',
        'custom_screeners',
        ['is_auto_trade_enabled', 'run_frequency'],
        unique=False
    )


def downgrade() -> None:
    """Remove auto-trade integration fields from custom_screeners table."""
    op.drop_index('ix_custom_screeners_auto_trade', table_name='custom_screeners')
    op.drop_column('custom_screeners', 'strategy_template_id')
    op.drop_column('custom_screeners', 'inferred_strategy_type')
    op.drop_column('custom_screeners', 'next_run_at')
    op.drop_column('custom_screeners', 'last_run_at')
    op.drop_column('custom_screeners', 'run_time')
    op.drop_column('custom_screeners', 'run_frequency')
    op.drop_column('custom_screeners', 'is_auto_trade_enabled')


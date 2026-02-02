"""add screener tables

Revision ID: screener_001
Revises: f08ed7317c2a
Create Date: 2026-01-23 10:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = 'screener_001'
down_revision: Union[str, None] = 'f08ed7317c2a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create screener tables."""
    # 1. custom_screeners - User-defined screener configurations
    op.create_table('custom_screeners',
        sa.Column('id', UUID(as_uuid=False), nullable=False),
        sa.Column('user_id', UUID(as_uuid=False), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('universe', sa.String(length=50), nullable=False, server_default='nifty500'),
        sa.Column('filters', JSONB(), nullable=False),
        sa.Column('min_score', sa.Float(), nullable=False, server_default='50.0'),
        sa.Column('top_n', sa.Integer(), nullable=False, server_default='50'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_custom_screeners_user', 'custom_screeners', ['user_id'], unique=False)
    op.create_index('ix_custom_screeners_name', 'custom_screeners', ['user_id', 'name'], unique=False)

    # 2. screener_runs - Record of screener executions
    op.create_table('screener_runs',
        sa.Column('id', UUID(as_uuid=False), nullable=False),
        sa.Column('user_id', UUID(as_uuid=False), nullable=False),
        sa.Column('custom_screener_id', UUID(as_uuid=False), nullable=True),
        sa.Column('preset', sa.String(length=50), nullable=True),
        sa.Column('universe', sa.String(length=50), nullable=False),
        sa.Column('filters', JSONB(), nullable=False),
        sa.Column('min_score', sa.Float(), nullable=False),
        sa.Column('top_n', sa.Integer(), nullable=False),
        sa.Column('total_screened', sa.Integer(), nullable=False),
        sa.Column('passed_count', sa.Integer(), nullable=False),
        sa.Column('duration_ms', sa.Integer(), nullable=False),
        sa.Column('executed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['custom_screener_id'], ['custom_screeners.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_screener_runs_user', 'screener_runs', ['user_id'], unique=False)
    op.create_index('ix_screener_runs_executed', 'screener_runs', ['executed_at'], unique=False)

    # 3. screener_results - Individual stock results from screener runs
    op.create_table('screener_results',
        sa.Column('id', UUID(as_uuid=False), nullable=False),
        sa.Column('run_id', UUID(as_uuid=False), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('passed', sa.Boolean(), nullable=False),
        sa.Column('filter_scores', JSONB(), nullable=False, server_default='{}'),
        sa.Column('reasons', JSONB(), nullable=False, server_default='[]'),
        sa.Column('extra_data', JSONB(), nullable=False, server_default='{}'),
        sa.ForeignKeyConstraint(['run_id'], ['screener_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_screener_results_run', 'screener_results', ['run_id'], unique=False)
    op.create_index('ix_screener_results_symbol', 'screener_results', ['symbol'], unique=False)

    # 4. daily_recommendations - Daily stock recommendations with performance tracking
    op.create_table('daily_recommendations',
        sa.Column('id', UUID(as_uuid=False), nullable=False),
        sa.Column('date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('price_at_rec', sa.Float(), nullable=False),
        sa.Column('price_1d', sa.Float(), nullable=True),
        sa.Column('price_1w', sa.Float(), nullable=True),
        sa.Column('price_1m', sa.Float(), nullable=True),
        sa.Column('return_1d', sa.Float(), nullable=True),
        sa.Column('return_1w', sa.Float(), nullable=True),
        sa.Column('return_1m', sa.Float(), nullable=True),
        sa.Column('filter_scores', JSONB(), nullable=False, server_default='{}'),
        sa.Column('reasons', JSONB(), nullable=False, server_default='[]'),
        sa.Column('extra_data', JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_daily_recommendations_date', 'daily_recommendations', ['date'], unique=False)
    op.create_index('ix_daily_recommendations_date_category', 'daily_recommendations', ['date', 'category'], unique=False)
    op.create_index('ix_daily_recommendations_symbol', 'daily_recommendations', ['symbol'], unique=False)


def downgrade() -> None:
    """Drop screener tables."""
    # Drop in reverse order due to foreign key dependencies
    op.drop_index('ix_daily_recommendations_symbol', table_name='daily_recommendations')
    op.drop_index('ix_daily_recommendations_date_category', table_name='daily_recommendations')
    op.drop_index('ix_daily_recommendations_date', table_name='daily_recommendations')
    op.drop_table('daily_recommendations')

    op.drop_index('ix_screener_results_symbol', table_name='screener_results')
    op.drop_index('ix_screener_results_run', table_name='screener_results')
    op.drop_table('screener_results')

    op.drop_index('ix_screener_runs_executed', table_name='screener_runs')
    op.drop_index('ix_screener_runs_user', table_name='screener_runs')
    op.drop_table('screener_runs')

    op.drop_index('ix_custom_screeners_name', table_name='custom_screeners')
    op.drop_index('ix_custom_screeners_user', table_name='custom_screeners')
    op.drop_table('custom_screeners')


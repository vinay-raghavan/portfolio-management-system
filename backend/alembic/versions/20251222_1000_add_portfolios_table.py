"""Add portfolios table and portfolio_id to related tables

Revision ID: add_portfolios
Revises: add_amo_fields
Create Date: 2025-12-22 10:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_portfolios'
down_revision: Union[str, None] = 'add_amo_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create portfolios table
    op.create_table(
        'portfolios',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('currency', sa.String(3), nullable=False, server_default='INR'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create indexes for portfolios
    op.create_index('ix_portfolios_user', 'portfolios', ['user_id'])
    op.create_index('ix_portfolios_user_default', 'portfolios', ['user_id', 'is_default'])
    
    # Add portfolio_id to positions table
    op.add_column('positions', sa.Column(
        'portfolio_id',
        postgresql.UUID(as_uuid=False),
        sa.ForeignKey('portfolios.id', ondelete='CASCADE'),
        nullable=True
    ))
    
    # Update positions indexes - drop old unique constraint and add new ones
    op.drop_index('ix_positions_user_symbol', table_name='positions')
    op.create_index('ix_positions_portfolio_symbol', 'positions', ['portfolio_id', 'symbol'], unique=True)
    op.create_index('ix_positions_user_symbol', 'positions', ['user_id', 'symbol'])
    
    # Add portfolio_id to trades table
    op.add_column('trades', sa.Column(
        'portfolio_id',
        postgresql.UUID(as_uuid=False),
        sa.ForeignKey('portfolios.id', ondelete='CASCADE'),
        nullable=True
    ))
    op.create_index('ix_trades_portfolio_executed', 'trades', ['portfolio_id', 'executed_at'])
    
    # Add portfolio_id to cost_lots table
    op.add_column('cost_lots', sa.Column(
        'portfolio_id',
        postgresql.UUID(as_uuid=False),
        sa.ForeignKey('portfolios.id', ondelete='CASCADE'),
        nullable=True
    ))
    op.create_index('ix_cost_lots_portfolio_symbol', 'cost_lots', ['portfolio_id', 'symbol'])


def downgrade() -> None:
    # Remove portfolio_id from cost_lots
    op.drop_index('ix_cost_lots_portfolio_symbol', table_name='cost_lots')
    op.drop_column('cost_lots', 'portfolio_id')
    
    # Remove portfolio_id from trades
    op.drop_index('ix_trades_portfolio_executed', table_name='trades')
    op.drop_column('trades', 'portfolio_id')
    
    # Remove portfolio_id from positions and restore old index
    op.drop_index('ix_positions_user_symbol', table_name='positions')
    op.drop_index('ix_positions_portfolio_symbol', table_name='positions')
    op.create_index('ix_positions_user_symbol', 'positions', ['user_id', 'symbol'], unique=True)
    op.drop_column('positions', 'portfolio_id')
    
    # Drop portfolios table
    op.drop_index('ix_portfolios_user_default', table_name='portfolios')
    op.drop_index('ix_portfolios_user', table_name='portfolios')
    op.drop_table('portfolios')


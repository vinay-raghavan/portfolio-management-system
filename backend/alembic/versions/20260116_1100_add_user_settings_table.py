"""Add user_settings table for user preferences

Revision ID: user_settings_001
Revises: broker_credentials_001
Create Date: 2026-01-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'user_settings_001'
down_revision: Union[str, None] = 'broker_credentials_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create user_settings table for user preferences."""
    op.create_table(
        'user_settings',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), 
                  sa.ForeignKey('users.id', ondelete='CASCADE'), 
                  nullable=False, unique=True, index=True),
        
        # Data provider preference
        sa.Column('data_provider', sa.String(50), nullable=False, default='yahoo'),
        
        # Market preference
        sa.Column('default_market', sa.String(10), nullable=False, default='IN'),
        
        # Display preferences
        sa.Column('currency', sa.String(10), nullable=False, default='INR'),
        sa.Column('theme', sa.String(20), nullable=False, default='system'),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), 
                  onupdate=sa.func.now()),
    )


def downgrade() -> None:
    """Drop user_settings table."""
    op.drop_table('user_settings')


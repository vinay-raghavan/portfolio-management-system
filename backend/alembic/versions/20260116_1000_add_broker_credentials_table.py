"""Add broker_credentials table for encrypted OAuth credentials

Revision ID: broker_credentials_001
Revises: 3aa7b40d5d20
Create Date: 2026-01-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'broker_credentials_001'
down_revision: Union[str, None] = '3aa7b40d5d20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create broker_credentials table with encrypted sensitive fields."""
    op.create_table(
        'broker_credentials',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('broker_type', sa.String(50), nullable=False, index=True),
        
        # Client ID (not encrypted - used for identification)
        sa.Column('client_id', sa.String(255), nullable=False),
        
        # Encrypted sensitive fields (Fernet AES-128-CBC encrypted)
        sa.Column('secret_key_encrypted', sa.Text(), nullable=False),
        sa.Column('access_token_encrypted', sa.Text(), nullable=True),
        
        # OAuth configuration
        sa.Column('redirect_uri', sa.String(500), nullable=False),
        
        # Token metadata
        sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        
        # Audit fields
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        
        # Ensure one credential per broker per user
        sa.UniqueConstraint('user_id', 'broker_type', name='uq_user_broker'),
    )
    
    # Add comment explaining encryption
    op.execute("""
        COMMENT ON TABLE broker_credentials IS 
        'Stores encrypted broker OAuth credentials. secret_key_encrypted and access_token_encrypted use Fernet (AES-128-CBC) encryption.';
    """)


def downgrade() -> None:
    """Drop broker_credentials table."""
    op.drop_table('broker_credentials')


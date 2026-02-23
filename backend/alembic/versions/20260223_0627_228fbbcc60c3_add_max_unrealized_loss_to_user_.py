"""add max_unrealized_loss to user_strategies

Revision ID: 228fbbcc60c3
Revises: ad231632e600
Create Date: 2026-02-23 06:27:38.993543+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '228fbbcc60c3'
down_revision: Union[str, None] = 'ad231632e600'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add max_unrealized_loss column to user_strategies
    # This triggers circuit breaker when open positions have too much unrealized loss
    op.add_column(
        'user_strategies',
        sa.Column('max_unrealized_loss', sa.Numeric(18, 2), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('user_strategies', 'max_unrealized_loss')


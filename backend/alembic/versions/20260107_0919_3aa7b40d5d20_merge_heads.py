"""merge_heads

Revision ID: 3aa7b40d5d20
Revises: add_profit_booking_rules, cb_persistence_001
Create Date: 2026-01-07 09:19:45.882599+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3aa7b40d5d20'
down_revision: Union[str, None] = ('add_profit_booking_rules', 'cb_persistence_001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass


"""Add sector concentration and intraday columns to risk_limits

Revision ID: 976587252025
Revises: b4c844c2eb96
Create Date: 2025-12-21 17:24:07.390574+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '976587252025'
down_revision: Union[str, None] = 'b4c844c2eb96'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to risk_limits table
    op.add_column('risk_limits', sa.Column(
        'max_sector_concentration',
        sa.Numeric(precision=5, scale=2),
        nullable=False,
        server_default=sa.text("'40'::numeric")  # 40% max in one sector
    ))
    op.add_column('risk_limits', sa.Column(
        'max_intraday_exposure',
        sa.Numeric(precision=18, scale=4),
        nullable=False,
        server_default=sa.text("'500000'::numeric")  # ₹5 Lakh default
    ))
    op.add_column('risk_limits', sa.Column(
        'auto_square_off_intraday',
        sa.Boolean(),
        nullable=False,
        server_default=sa.text('true')
    ))


def downgrade() -> None:
    op.drop_column('risk_limits', 'auto_square_off_intraday')
    op.drop_column('risk_limits', 'max_intraday_exposure')
    op.drop_column('risk_limits', 'max_sector_concentration')


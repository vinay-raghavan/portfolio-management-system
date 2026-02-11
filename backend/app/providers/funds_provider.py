"""Database-backed funds provider for PaperBroker.

This module provides a FundsProvider implementation for the backend,
using the shared DatabaseFundsProvider with proper models.

Supports CNC (Delivery), MIS (Intraday), and MTF (Margin) product types.
"""

from decimal import Decimal

from shared.providers.funds.database_provider import (
    DatabaseFundsProvider as SharedDatabaseFundsProvider,
)
from shared.providers.schemas import Funds, ProductType
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.portfolio.models import Position, UserFunds


class DatabaseFundsProvider(SharedDatabaseFundsProvider):
    """Database-backed funds provider for the backend.

    Uses the shared DatabaseFundsProvider with backend-specific models.
    Supports all product types: DELIVERY, INTRADAY, MARGIN.
    """

    def __init__(self, db: AsyncSession, initial_balance: Decimal = Decimal("100000")):
        """Initialize with database session and backend models.

        Args:
            db: SQLAlchemy async session
            initial_balance: Default balance for new users
        """
        super().__init__(
            db=db,
            user_funds_model=UserFunds,
            initial_balance=initial_balance,
            position_model=Position,
            algo_position_model=None,  # Backend doesn't use algo positions
        )


# Export ProductType for convenience
__all__ = ["DatabaseFundsProvider", "ProductType", "Funds"]

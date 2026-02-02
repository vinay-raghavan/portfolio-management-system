"""User broker selection for live trading strategies.

This module provides helpers to get the appropriate broker for a user
based on their connected broker credentials.
"""

import logging
from decimal import Decimal

from shared.providers.broker import PaperBroker
from shared.providers.funds import DatabaseFundsProvider
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from engine.config import settings
from engine.models.algo import UserFunds
from engine.models.broker import BrokerCredential, BrokerType
from engine.providers.broker import Broker, get_broker

logger = logging.getLogger(__name__)


async def get_user_broker(
    db: AsyncSession,
    user_id: str,
    is_paper_trading: bool = True,
) -> Broker:
    """Get the appropriate broker for a user based on their settings.

    For paper trading strategies, returns the global paper broker.
    For live trading strategies, looks up the user's connected broker
    credentials and creates a broker instance.

    Args:
        db: Database session
        user_id: User ID
        is_paper_trading: Whether this is a paper trading strategy

    Returns:
        Broker instance (paper or live based on settings)
    """
    # Paper trading always uses paper broker with database-backed funds
    if is_paper_trading:
        logger.debug(f"Using paper broker for user {user_id[:8]}... (paper trading mode)")
        broker = get_broker("paper")
        # Configure DatabaseFundsProvider for database-backed funds management
        if isinstance(broker, PaperBroker):
            initial_balance = Decimal(str(settings.PAPER_TRADING_INITIAL_BALANCE))
            funds_provider = DatabaseFundsProvider(
                db=db,
                user_funds_model=UserFunds,
                initial_balance=initial_balance,
            )
            broker.set_funds_provider(funds_provider)
            logger.debug("Configured DatabaseFundsProvider for paper broker")
        return broker

    # For live trading, look up user's connected broker credentials
    result = await db.execute(
        select(BrokerCredential).where(
            BrokerCredential.user_id == user_id,
            BrokerCredential.is_active.is_(True),
        )
    )
    credentials = list(result.scalars().all())

    # Find a connected broker (one with valid access token)
    for cred in credentials:
        if cred.is_connected and cred.access_token:
            broker = await _create_broker_from_credential(cred)
            if broker:
                logger.info(
                    f"Using {cred.broker_type} broker for user {user_id[:8]}... (live trading)"
                )
                return broker

    # No connected broker found - fall back to paper broker with warning
    logger.warning(
        f"No connected broker found for user {user_id[:8]}... "
        f"Live trading strategy will use paper broker! "
        f"User should connect a broker in settings."
    )
    broker = get_broker("paper")
    # Configure DatabaseFundsProvider for the fallback paper broker too
    if isinstance(broker, PaperBroker):
        initial_balance = Decimal(str(settings.PAPER_TRADING_INITIAL_BALANCE))
        funds_provider = DatabaseFundsProvider(
            db=db,
            user_funds_model=UserFunds,
            initial_balance=initial_balance,
        )
        broker.set_funds_provider(funds_provider)
    return broker


async def _create_broker_from_credential(cred: BrokerCredential) -> Broker | None:
    """Create a broker instance from user credentials.

    Args:
        cred: Broker credential with decrypted access token

    Returns:
        Broker instance or None if broker type not supported
    """
    broker_type = cred.broker_type.lower()

    if broker_type == BrokerType.FYERS.value:
        try:
            from shared.providers.broker import FyersBroker

            broker = FyersBroker(
                access_token=cred.access_token,
                client_id=cred.client_id,
            )
            # Try to connect to verify credentials
            if await broker.connect():
                return broker
            else:
                logger.warning(f"Failed to connect Fyers broker for user {cred.user_id[:8]}...")
                return None
        except ImportError:
            logger.error("FyersBroker not available - fyers-apiv3 package not installed")
            return None
        except Exception as e:
            logger.error(f"Failed to create Fyers broker: {e}")
            return None

    # Add more broker types here as they are implemented
    # elif broker_type == BrokerType.ZERODHA.value:
    #     ...

    logger.warning(f"Unsupported broker type: {broker_type}")
    return None


async def get_connected_broker_type(db: AsyncSession, user_id: str) -> str | None:
    """Get the broker type that the user has connected.

    Args:
        db: Database session
        user_id: User ID

    Returns:
        Broker type string or None if no broker connected
    """
    result = await db.execute(
        select(BrokerCredential).where(
            BrokerCredential.user_id == user_id,
            BrokerCredential.is_active.is_(True),
        )
    )
    credentials = list(result.scalars().all())

    for cred in credentials:
        if cred.is_connected:
            return cred.broker_type

    return None

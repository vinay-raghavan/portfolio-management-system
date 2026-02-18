"""Market data service using provider abstraction."""

import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.data.schemas import (
    HistoricalDataPoint,
    HistoricalDataResponse,
    IndexConstituent,
    IndexConstituentsResponse,
    StockInfo,
    StockQuote,
)
from app.providers.data import DataProvider, get_data_provider

logger = logging.getLogger(__name__)


async def _get_provider_for_setting(
    db: AsyncSession, user_id: str, provider_setting: str
) -> DataProvider | None:
    """Get a data provider instance based on a provider setting value.

    Args:
        db: Database session
        user_id: User ID
        provider_setting: Provider setting value (yahoo, fyers, nse)

    Returns:
        DataProvider instance or None to use default (Yahoo)
    """
    from shared.providers.data.fyers import FyersDataProvider

    from app.modules.broker.models import BrokerCredential

    if provider_setting == "yahoo":
        # Use default Yahoo provider
        return None

    if provider_setting == "fyers":
        # Get Fyers credentials
        result = await db.execute(
            select(BrokerCredential).where(
                BrokerCredential.user_id == user_id,
                BrokerCredential.broker_type == "fyers",
            )
        )
        cred = result.scalar_one_or_none()

        if cred and cred.access_token_encrypted:
            # Get decrypted access token
            access_token = cred.access_token
            if access_token:
                logger.info(f"Using Fyers data provider for user {user_id[:8]}...")
                return FyersDataProvider(
                    access_token=access_token,
                    client_id=cred.client_id,
                    log_path="/tmp",  # Use /tmp for Chainguard containers (no write to /app)  # nosec B108
                )
        logger.warning(
            f"Fyers selected but not connected for user {user_id[:8]}, falling back to default"
        )
        return None

    if provider_setting == "nse":
        # NSE provider doesn't need special credentials
        return get_data_provider("nse")

    # Unknown provider, use default
    return None


async def get_user_data_provider(db: AsyncSession, user_id: str) -> DataProvider | None:
    """Get a data provider instance based on user's real-time data settings.

    Args:
        db: Database session
        user_id: User ID

    Returns:
        DataProvider instance configured for the user, or None to use default
    """
    from app.modules.settings.models import UserSettings

    # Get user settings
    result = await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    settings = result.scalar_one_or_none()

    if not settings:
        return None

    return await _get_provider_for_setting(db, user_id, settings.data_provider)


async def get_user_research_data_provider(db: AsyncSession, user_id: str) -> DataProvider | None:
    """Get a data provider instance based on user's research/fundamental data settings.

    This is separate from real-time data provider because fundamental data
    quality varies by provider. Yahoo tends to have better fundamental data.

    Args:
        db: Database session
        user_id: User ID

    Returns:
        DataProvider instance configured for the user, or None to use default (Yahoo)
    """
    from app.modules.settings.models import UserSettings

    # Get user settings
    result = await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    settings = result.scalar_one_or_none()

    if not settings:
        return None

    return await _get_provider_for_setting(db, user_id, settings.research_data_provider)


class MarketDataService:
    """Service for fetching market data using configurable data providers.

    This service acts as a bridge between the API layer and the data provider
    abstraction. It converts provider schemas to module-specific schemas.
    """

    def __init__(self, provider: DataProvider | None = None):
        """Initialize with optional custom provider.

        Args:
            provider: Data provider instance. If None, uses default from config.
        """
        self._provider = provider or get_data_provider()

    async def get_current_price(self, symbol: str) -> Decimal | None:
        """Get current price for a symbol."""
        price = await self._provider.get_current_price(symbol)
        if price is not None:
            return Decimal(str(price))
        return None

    async def get_quote(self, symbol: str) -> StockQuote | None:
        """Get full quote for a symbol including extended hours data."""
        from app.modules.data.schemas import MarketSession as APIMarketSession

        quote = await self._provider.get_quote(symbol)
        if quote is None:
            return None

        # Convert provider's MarketSession to API's MarketSession
        api_market_session = None
        if quote.market_session:
            session_map = {
                "PRE_MARKET": APIMarketSession.PRE_MARKET,
                "REGULAR": APIMarketSession.REGULAR,
                "POST_MARKET": APIMarketSession.POST_MARKET,
                "CLOSED": APIMarketSession.CLOSED,
            }
            api_market_session = session_map.get(quote.market_session.value)

        return StockQuote(
            symbol=quote.symbol,
            price=quote.price,
            open=quote.open,
            high=quote.high,
            low=quote.low,
            close=quote.close,
            volume=quote.volume,
            change=quote.change,
            change_pct=quote.change_percent,
            timestamp=quote.timestamp,
            # Extended hours data
            pre_market_price=quote.pre_market_price,
            pre_market_change=quote.pre_market_change,
            pre_market_change_pct=quote.pre_market_change_percent,
            pre_market_time=quote.pre_market_time,
            post_market_price=quote.post_market_price,
            post_market_change=quote.post_market_change,
            post_market_change_pct=quote.post_market_change_percent,
            post_market_time=quote.post_market_time,
            market_session=api_market_session,
        )

    async def get_stock_info(self, symbol: str) -> StockInfo | None:
        """Get detailed stock information."""
        info = await self._provider.get_instrument_info(symbol)
        if info is None:
            return None

        return StockInfo(
            symbol=info.symbol,
            name=info.name,
            exchange=info.exchange,
            sector=info.sector,
            industry=info.industry,
        )

    async def get_historical_data(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> HistoricalDataResponse | None:
        """Get historical price data."""
        ohlcv_list = await self._provider.get_historical(symbol, period, interval)
        if not ohlcv_list:
            return None

        data_points = [
            HistoricalDataPoint(
                date=ohlcv.timestamp,
                open=ohlcv.open,
                high=ohlcv.high,
                low=ohlcv.low,
                close=ohlcv.close,
                volume=ohlcv.volume,
            )
            for ohlcv in ohlcv_list
        ]

        return HistoricalDataResponse(
            symbol=symbol.upper(),
            interval=interval,
            data=data_points,
        )

    async def search_symbols(self, query: str) -> list[dict]:
        """Search for symbols by name or ticker."""
        results = await self._provider.search_symbols(query)
        return [
            {
                "symbol": r.symbol,
                "name": r.name,
                "exchange": r.exchange,
                "type": r.instrument_type,
            }
            for r in results
        ]

    async def get_market_status(self) -> dict:
        """Get current market status.

        Returns:
            Dict with market status information.
        """
        from datetime import datetime

        from app.core.config import settings

        # Check if provider has market status method
        if hasattr(self._provider, "get_market_status"):
            status = await self._provider.get_market_status()
            status["market"] = settings.DEFAULT_MARKET
            return status

        # Fallback for providers without market status
        is_open = await self._provider.is_market_open()
        result = {
            "is_open": is_open,
            "status": "open" if is_open else "closed",
            "market": settings.DEFAULT_MARKET,
            "timestamp": datetime.now().isoformat(),
        }

        # Add next open time if provider supports it
        if hasattr(self._provider, "get_next_market_open"):
            result["next_open"] = self._provider.get_next_market_open().isoformat()

        return result

    async def get_index_constituents(self, index: str) -> IndexConstituentsResponse | None:
        """Get constituents of an index.

        Args:
            index: Index name (e.g., "NIFTY 50", "NIFTY 500")

        Returns:
            IndexConstituentsResponse with list of constituent stocks
        """
        # Check if provider supports index constituents
        if not hasattr(self._provider, "get_index_constituents"):
            logger.warning(
                f"Provider {type(self._provider).__name__} does not support index constituents"
            )
            return None

        constituents_data = await self._provider.get_index_constituents(index)
        if not constituents_data:
            return None

        constituents = [
            IndexConstituent(
                symbol=c["symbol"],
                name=c.get("name"),
                industry=c.get("industry"),
                isin=c.get("isin"),
                series=c.get("series", "EQ"),
                is_fno=c.get("is_fno", False),
                last_price=c.get("last_price"),
                change=c.get("change"),
                change_pct=c.get("change_pct"),
                open=c.get("open"),
                high=c.get("high"),
                low=c.get("low"),
                previous_close=c.get("previous_close"),
                volume=c.get("volume"),
                year_high=c.get("year_high"),
                year_low=c.get("year_low"),
            )
            for c in constituents_data
        ]

        return IndexConstituentsResponse(
            index=index.upper(),
            count=len(constituents),
            constituents=constituents,
        )

"""Signal generation and management service."""

import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import uuid4

import pandas as pd
import yfinance as yf
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.signals.models import Signal, SignalStatus, SignalType
from app.modules.signals.strategies import SignalData, StrategyRegistry

logger = logging.getLogger(__name__)


class SignalService:
    """Service for generating and managing trading signals."""

    def __init__(self, db: AsyncSession):
        """Initialize signal service.

        Args:
            db: Database session
        """
        self.db = db

    def _normalize_symbol(self, symbol: str) -> str:
        """Normalize symbol for Yahoo Finance."""
        symbol = symbol.upper().strip()

        if "." in symbol:
            return symbol

        default_market = getattr(settings, "DEFAULT_MARKET", "US").upper()
        if default_market in ("NSE", "IN", "INDIA"):
            return f"{symbol}.NS"
        elif default_market == "BSE":
            return f"{symbol}.BO"

        return symbol

    def _get_historical_data(
        self, symbol: str, period: str = "6mo", interval: str = "1d"
    ) -> pd.DataFrame | None:
        """Fetch historical OHLCV data for a symbol.

        Args:
            symbol: Stock symbol
            period: Data period (e.g., "6mo", "1y")
            interval: Data interval (e.g., "1d", "1h")

        Returns:
            DataFrame with OHLCV data or None
        """
        try:
            yahoo_symbol = self._normalize_symbol(symbol)
            ticker = yf.Ticker(yahoo_symbol)
            hist = ticker.history(period=period, interval=interval)

            if (hist.empty or len(hist) < 50) and yahoo_symbol.endswith((".NS", ".BO")):
                # Try without suffix if Indian market
                ticker = yf.Ticker(symbol.upper().strip())
                hist = ticker.history(period=period, interval=interval)

            if hist.empty:
                logger.warning(f"No data found for {symbol}")
                return None

            return hist
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return None

    async def generate_signals(
        self,
        symbols: list[str],
        user_id: str,
        strategy_name: str | None = None,
        timeframe: str = "1d",
    ) -> list[Signal]:
        """Generate trading signals for given symbols.

        Args:
            symbols: List of stock symbols
            user_id: ID of the user generating signals
            strategy_name: Specific strategy to use (None = all strategies)
            timeframe: Timeframe for analysis

        Returns:
            List of generated Signal objects
        """
        signals: list[Signal] = []

        # Get strategies to run
        if strategy_name:
            strategy = StrategyRegistry.get(strategy_name)
            if not strategy:
                logger.error(f"Strategy not found: {strategy_name}")
                return []
            strategies = [strategy]
        else:
            strategies = StrategyRegistry.get_all()

        if not strategies:
            logger.warning("No strategies registered")
            return []

        # Map timeframe to yfinance period
        period_map = {"1d": "6mo", "1h": "1mo", "4h": "3mo", "1w": "2y"}
        period = period_map.get(timeframe, "6mo")

        for symbol in symbols:
            df = self._get_historical_data(symbol, period=period, interval=timeframe)
            if df is None:
                continue

            for strategy in strategies:
                try:
                    signal_data_list = strategy.generate_signals(df, symbol)

                    for signal_data in signal_data_list:
                        signal = self._create_signal_from_data(
                            signal_data, user_id, strategy.name, timeframe
                        )
                        self.db.add(signal)
                        signals.append(signal)

                except Exception as e:
                    logger.error(f"Error generating signals for {symbol} with {strategy.name}: {e}")

        if signals:
            await self.db.commit()
            for signal in signals:
                await self.db.refresh(signal)

        return signals

    def _create_signal_from_data(
        self, data: SignalData, user_id: str, strategy_name: str, timeframe: str
    ) -> Signal:
        """Create Signal model from SignalData."""
        return Signal(
            id=str(uuid4()),
            user_id=user_id,
            symbol=data.symbol.upper(),
            signal_type=data.signal_type,
            strength=data.strength,
            confidence=data.confidence,
            strategy_name=strategy_name,
            timeframe=timeframe,
            price_at_signal=data.price_at_signal,
            entry_price=data.entry_price,
            stop_loss=data.stop_loss,
            take_profit=data.take_profit,
            risk_reward_ratio=data.risk_reward_ratio,
            indicators=data.indicators,
            notes=data.notes,
            status=SignalStatus.PENDING.value,
        )

    async def get_signal(self, signal_id: str, user_id: str) -> Signal | None:
        """Get a signal by ID.

        Args:
            signal_id: Signal ID
            user_id: User ID (for authorization)

        Returns:
            Signal or None if not found
        """
        result = await self.db.execute(
            select(Signal).where(Signal.id == signal_id, Signal.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_signals(
        self,
        user_id: str,
        symbol: str | None = None,
        status: SignalStatus | None = None,
        signal_type: SignalType | None = None,
        strategy_name: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Sequence[Signal], int]:
        """Get signals for a user with filtering.

        Returns:
            Tuple of (signals, total_count)
        """
        query = select(Signal).where(Signal.user_id == user_id)

        if symbol:
            query = query.where(Signal.symbol == symbol.upper())
        if status:
            query = query.where(Signal.status == status.value)
        if signal_type:
            query = query.where(Signal.signal_type == signal_type.value)
        if strategy_name:
            query = query.where(Signal.strategy_name == strategy_name)

        # Get total count
        from sqlalchemy import func

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Get paginated results
        query = query.order_by(Signal.generated_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        signals = result.scalars().all()

        return signals, total

    async def update_signal(
        self,
        signal_id: str,
        user_id: str,
        status: SignalStatus | None = None,
        is_executed: bool | None = None,
        executed_order_id: str | None = None,
        notes: str | None = None,
    ) -> Signal | None:
        """Update a signal.

        Args:
            signal_id: Signal ID
            user_id: User ID
            status: New status
            is_executed: Execution flag
            executed_order_id: Order ID if executed
            notes: Updated notes

        Returns:
            Updated Signal or None
        """
        signal = await self.get_signal(signal_id, user_id)
        if not signal:
            return None

        if status is not None:
            signal.status = status.value
        if is_executed is not None:
            signal.is_executed = is_executed
            if is_executed:
                signal.executed_at = datetime.now(UTC)
        if executed_order_id is not None:
            signal.executed_order_id = executed_order_id
        if notes is not None:
            signal.notes = notes

        await self.db.commit()
        await self.db.refresh(signal)
        return signal

    async def cancel_signal(self, signal_id: str, user_id: str) -> Signal | None:
        """Cancel a pending signal.

        Args:
            signal_id: Signal ID
            user_id: User ID

        Returns:
            Cancelled Signal or None
        """
        signal = await self.get_signal(signal_id, user_id)
        if not signal or signal.status != SignalStatus.PENDING.value:
            return None

        signal.status = SignalStatus.CANCELLED.value
        await self.db.commit()
        await self.db.refresh(signal)
        return signal

    async def expire_old_signals(self, user_id: str | None = None) -> int:
        """Expire signals past their expiration date.

        Args:
            user_id: Optional user ID to limit scope

        Returns:
            Number of signals expired
        """
        query = select(Signal).where(
            Signal.status == SignalStatus.PENDING.value,
            Signal.expires_at.isnot(None),
            Signal.expires_at < datetime.now(UTC),
        )

        if user_id:
            query = query.where(Signal.user_id == user_id)

        result = await self.db.execute(query)
        signals = result.scalars().all()

        for signal in signals:
            signal.status = SignalStatus.EXPIRED.value

        if signals:
            await self.db.commit()

        return len(signals)

    def get_available_strategies(self) -> list[dict]:
        """Get list of available strategies.

        Returns:
            List of strategy info dictionaries
        """
        return StrategyRegistry.list_strategies()

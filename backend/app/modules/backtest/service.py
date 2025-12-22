"""Backtest service for managing and running backtests."""

import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pandas as pd
import yfinance as yf
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.modules.backtest.models import BacktestResult, BacktestStatus, BacktestTrade
from app.modules.backtest.runner import BacktestConfig, BacktestRunner
from app.modules.backtest.schemas import BacktestRequest
from app.modules.signals.strategies.registry import StrategyRegistry


class BacktestService:
    """Service for managing backtest operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _normalize_symbol(self, symbol: str) -> str:
        """Normalize symbol for Yahoo Finance.

        For Indian market (NSE/BSE), adds the appropriate suffix.
        For other markets, returns the symbol as-is.
        """
        symbol = symbol.upper().strip()

        # Already has Yahoo Finance suffix
        if "." in symbol:
            return symbol

        # Check if default market is Indian
        default_market = getattr(settings, "DEFAULT_MARKET", "US").upper()
        if default_market in ("NSE", "IN", "INDIA"):
            return f"{symbol}.NS"
        elif default_market == "BSE":
            return f"{symbol}.BO"

        return symbol

    async def create_backtest(self, user_id: str, request: BacktestRequest) -> BacktestResult:
        """Create a new backtest record.

        Args:
            user_id: User ID
            request: Backtest request parameters

        Returns:
            Created BacktestResult
        """
        backtest = BacktestResult(
            id=str(uuid4()),
            user_id=user_id,
            strategy_name=request.strategy_name,
            symbol=request.symbol,
            timeframe=request.timeframe,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=request.initial_capital,
            strategy_params=request.strategy_params,
            status=BacktestStatus.PENDING.value,
        )

        self.db.add(backtest)
        await self.db.commit()
        await self.db.refresh(backtest)

        return backtest

    async def run_backtest(self, backtest_id: str) -> BacktestResult:
        """Run a backtest and update results.

        Args:
            backtest_id: ID of the backtest to run

        Returns:
            Updated BacktestResult with metrics
        """
        # Get backtest record (don't load trades yet, we'll create them)
        backtest = await self.get_backtest(backtest_id, include_trades=False)
        if not backtest:
            raise ValueError(f"Backtest {backtest_id} not found")

        # Update status to running
        backtest.status = BacktestStatus.RUNNING.value
        backtest.started_at = datetime.now(UTC)
        await self.db.commit()

        # Extract all needed values from the ORM object BEFORE entering the thread
        # This prevents SQLAlchemy lazy loading issues in the thread
        symbol = backtest.symbol
        start_date = backtest.start_date
        end_date = backtest.end_date
        timeframe = backtest.timeframe
        initial_capital = backtest.initial_capital
        strategy_name = backtest.strategy_name
        strategy_params = backtest.strategy_params or {}

        try:
            # Get strategy
            strategy = StrategyRegistry.get_strategy(strategy_name, strategy_params)
            if not strategy:
                raise ValueError(f"Strategy {strategy_name} not found")

            # Run the blocking operations in a thread to avoid blocking the async event loop
            # Pass only primitive values, not ORM objects
            result = await asyncio.to_thread(
                self._run_backtest_sync,
                symbol,
                start_date,
                end_date,
                timeframe,
                initial_capital,
                strategy,
            )

            # Update backtest with results
            await self._update_backtest_results(backtest, result)

            # Re-fetch backtest with trades eagerly loaded for response
            backtest = await self.get_backtest(backtest_id, include_trades=True)
            return backtest

        except Exception as e:
            backtest.status = BacktestStatus.FAILED.value
            backtest.error_message = str(e)
            backtest.completed_at = datetime.now(UTC)
            await self.db.commit()
            raise

    def _run_backtest_sync(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str,
        initial_capital: Any,
        strategy: Any,
    ) -> Any:
        """Run backtest synchronously (for use in a thread).

        This method fetches data and runs the backtest engine.
        It's designed to be run in a separate thread via asyncio.to_thread().
        """
        # Fetch historical data
        data = self._fetch_historical_data(symbol, start_date, end_date, timeframe)

        # Configure and run backtest
        config = BacktestConfig(
            symbol=symbol,
            strategy=strategy,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
        )

        runner = BacktestRunner(config)
        return runner.run(data)

    async def get_backtest(
        self, backtest_id: str, include_trades: bool = True
    ) -> BacktestResult | None:
        """Get a backtest by ID.

        Args:
            backtest_id: ID of the backtest to retrieve
            include_trades: Whether to eagerly load trades (default True)

        Returns:
            BacktestResult or None if not found
        """
        query = select(BacktestResult).where(BacktestResult.id == backtest_id)
        if include_trades:
            query = query.options(selectinload(BacktestResult.trades))
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_user_backtests(
        self, user_id: str, limit: int = 50, offset: int = 0
    ) -> list[BacktestResult]:
        """Get all backtests for a user."""
        result = await self.db.execute(
            select(BacktestResult)
            .where(BacktestResult.user_id == user_id)
            .order_by(BacktestResult.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def delete_backtest(self, backtest_id: str, user_id: str) -> bool:
        """Delete a backtest."""
        backtest = await self.get_backtest(backtest_id)
        if not backtest or backtest.user_id != user_id:
            return False

        await self.db.delete(backtest)
        await self.db.commit()
        return True

    def _fetch_historical_data(
        self, symbol: str, start_date: datetime, end_date: datetime, timeframe: str
    ) -> pd.DataFrame:
        """Fetch historical OHLCV data for backtesting."""
        # Map timeframe to yfinance interval
        interval_map = {
            "1m": "1m",
            "5m": "5m",
            "15m": "15m",
            "1h": "1h",
            "1d": "1d",
            "1wk": "1wk",
        }
        interval = interval_map.get(timeframe, "1d")

        # Normalize symbol for Yahoo Finance
        normalized_symbol = self._normalize_symbol(symbol)
        ticker = yf.Ticker(normalized_symbol)
        data = ticker.history(start=start_date, end=end_date, interval=interval)

        if data.empty:
            raise ValueError(f"No data available for {symbol}")

        # Normalize column names
        data.columns = [c.lower() for c in data.columns]
        return data

    async def _update_backtest_results(self, backtest: BacktestResult, result: Any) -> None:
        """Update backtest record with results from runner."""
        backtest.status = BacktestStatus.COMPLETED.value
        backtest.completed_at = datetime.now(UTC)

        # Performance metrics
        backtest.final_capital = result.final_capital
        backtest.total_return = result.total_return
        backtest.annualized_return = result.annualized_return
        backtest.sharpe_ratio = result.sharpe_ratio
        backtest.sortino_ratio = result.sortino_ratio
        backtest.max_drawdown = result.max_drawdown
        backtest.calmar_ratio = result.calmar_ratio

        # Trade statistics
        backtest.total_trades = result.total_trades
        backtest.winning_trades = result.winning_trades
        backtest.losing_trades = result.losing_trades
        backtest.win_rate = result.win_rate
        backtest.profit_factor = result.profit_factor
        backtest.avg_win = result.avg_win
        backtest.avg_loss = result.avg_loss
        backtest.avg_trade = result.avg_trade
        backtest.largest_win = result.largest_win
        backtest.largest_loss = result.largest_loss

        # Curves
        backtest.equity_curve = result.equity_curve
        backtest.drawdown_curve = result.drawdown_curve

        # Save trades
        for trade in result.trades:
            bt_trade = BacktestTrade(
                id=str(uuid4()),
                backtest_id=backtest.id,
                symbol=trade.symbol,
                side=trade.side,
                entry_date=trade.entry_date,
                entry_price=trade.entry_price,
                exit_date=trade.exit_date,
                exit_price=trade.exit_price,
                quantity=trade.quantity,
                pnl=trade.pnl,
                pnl_pct=trade.pnl_pct,
                is_winner=trade.is_winner,
                exit_reason=trade.exit_reason,
                signal_indicators=trade.signal_indicators,
            )
            self.db.add(bt_trade)

        await self.db.commit()
        await self.db.refresh(backtest)

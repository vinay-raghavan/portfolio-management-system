"""Core backtest runner engine.

This module provides the BacktestRunner class that simulates trading
based on strategy signals and calculates performance metrics.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

import pandas as pd

from app.modules.signals.strategies.base import BaseStrategy, SignalData


@dataclass
class Trade:
    """Represents a single trade in the backtest."""

    symbol: str
    side: str  # LONG or SHORT
    entry_date: datetime
    entry_price: Decimal
    quantity: int
    exit_date: datetime | None = None
    exit_price: Decimal | None = None
    pnl: Decimal | None = None
    pnl_pct: Decimal | None = None
    is_winner: bool | None = None
    exit_reason: str | None = None
    signal_indicators: dict[str, Any] | None = None


@dataclass
class BacktestConfig:
    """Configuration for a backtest run."""

    symbol: str
    strategy: BaseStrategy
    start_date: datetime
    end_date: datetime
    initial_capital: Decimal = Decimal("100000")
    position_size_pct: Decimal = Decimal("0.1")  # 10% of capital per trade
    commission_pct: Decimal = Decimal("0.001")  # 0.1% commission
    slippage_pct: Decimal = Decimal("0.0005")  # 0.05% slippage
    stop_loss_pct: Decimal | None = None  # Optional stop loss
    take_profit_pct: Decimal | None = None  # Optional take profit


@dataclass
class BacktestResult:
    """Result of a backtest run."""

    # Configuration
    symbol: str
    strategy_name: str
    start_date: datetime
    end_date: datetime
    initial_capital: Decimal
    final_capital: Decimal

    # Performance metrics
    total_return: Decimal
    annualized_return: Decimal
    sharpe_ratio: Decimal
    sortino_ratio: Decimal
    max_drawdown: Decimal
    calmar_ratio: Decimal

    # Trade statistics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: Decimal
    profit_factor: Decimal
    avg_win: Decimal
    avg_loss: Decimal
    avg_trade: Decimal
    largest_win: Decimal
    largest_loss: Decimal

    # Data
    trades: list[Trade] = field(default_factory=list)
    equity_curve: list[dict[str, Any]] = field(default_factory=list)
    drawdown_curve: list[dict[str, Any]] = field(default_factory=list)


class BacktestRunner:
    """Core backtest engine that simulates trading based on strategy signals."""

    def __init__(self, config: BacktestConfig):
        self.config = config
        self.capital = config.initial_capital
        self.position: Trade | None = None
        self.trades: list[Trade] = []
        self.equity_curve: list[dict[str, Any]] = []
        self.peak_equity = config.initial_capital
        self.max_drawdown = Decimal("0")

    def run(self, data: pd.DataFrame) -> BacktestResult:
        """Run the backtest on historical data.

        Args:
            data: DataFrame with OHLCV data (columns: open, high, low, close, volume)
                  Index should be datetime

        Returns:
            BacktestResult with all metrics and trades
        """
        if data.empty:
            raise ValueError("No data provided for backtest")

        # Ensure data is sorted by date
        data = data.sort_index()

        # Filter data to date range
        data = data[(data.index >= self.config.start_date) & (data.index <= self.config.end_date)]

        if data.empty:
            raise ValueError("No data in specified date range")

        # Generate signals for all data
        signals = self._generate_signals(data)

        # Simulate trading
        for i, (date, row) in enumerate(data.iterrows()):
            current_price = Decimal(str(row["close"]))

            # Check for stop loss / take profit if in position
            if self.position:
                self._check_exit_conditions(date, row)

            # Process signal if not in position
            if not self.position and i < len(signals):
                signal = signals[i]
                if signal and signal.signal_type in ["BUY", "SELL"]:
                    self._enter_position(date, current_price, signal)

            # Check for exit signal if in position
            elif self.position and i < len(signals):
                signal = signals[i]
                if signal and (
                    (self.position.side == "LONG" and signal.signal_type == "SELL")
                    or (self.position.side == "SHORT" and signal.signal_type == "BUY")
                ):
                    self._exit_position(date, current_price, "SIGNAL")

            # Record equity
            self._record_equity(date, current_price)

        # Close any open position at end
        if self.position:
            final_price = Decimal(str(data.iloc[-1]["close"]))
            self._exit_position(data.index[-1], final_price, "END_OF_BACKTEST")

        return self._calculate_results(data)

    def _generate_signals(self, data: pd.DataFrame) -> list[SignalData | None]:
        """Generate signals for all data points."""
        signals = []
        for i in range(len(data)):
            # Use data up to current point for signal generation
            historical_data = data.iloc[: i + 1]
            if len(historical_data) >= 20:  # Minimum data for indicators
                signal = self.config.strategy.generate_signal(self.config.symbol, historical_data)
                signals.append(signal)
            else:
                signals.append(None)
        return signals

    def _enter_position(self, date: datetime, price: Decimal, signal: SignalData) -> None:
        """Enter a new position."""
        # Apply slippage
        slippage = price * self.config.slippage_pct
        entry_price = price + slippage if signal.signal_type == "BUY" else price - slippage

        # Calculate position size
        position_value = self.capital * self.config.position_size_pct
        quantity = int(position_value / entry_price)

        if quantity <= 0:
            return

        # Apply commission
        commission = entry_price * quantity * self.config.commission_pct
        self.capital -= commission

        self.position = Trade(
            symbol=self.config.symbol,
            side="LONG" if signal.signal_type == "BUY" else "SHORT",
            entry_date=date,
            entry_price=entry_price,
            quantity=quantity,
            signal_indicators=signal.indicators,
        )

    def _exit_position(self, date: datetime, price: Decimal, reason: str) -> None:
        """Exit current position."""
        if not self.position:
            return

        # Apply slippage
        slippage = price * self.config.slippage_pct
        exit_price = price - slippage if self.position.side == "LONG" else price + slippage

        # Calculate P&L
        if self.position.side == "LONG":
            pnl = (exit_price - self.position.entry_price) * self.position.quantity
        else:
            pnl = (self.position.entry_price - exit_price) * self.position.quantity

        # Apply commission
        commission = exit_price * self.position.quantity * self.config.commission_pct
        pnl -= commission

        # Update position
        self.position.exit_date = date
        self.position.exit_price = exit_price
        self.position.pnl = pnl
        self.position.pnl_pct = (pnl / (self.position.entry_price * self.position.quantity)) * 100
        self.position.is_winner = pnl > 0
        self.position.exit_reason = reason

        # Update capital
        self.capital += pnl

        # Record trade
        self.trades.append(self.position)
        self.position = None

    def _check_exit_conditions(self, date: datetime, row: pd.Series) -> None:
        """Check stop loss and take profit conditions."""
        if not self.position:
            return

        high = Decimal(str(row["high"]))
        low = Decimal(str(row["low"]))

        if self.position.side == "LONG":
            # Check stop loss
            if self.config.stop_loss_pct:
                sl_price = self.position.entry_price * (1 - self.config.stop_loss_pct)
                if low <= sl_price:
                    self._exit_position(date, sl_price, "STOP_LOSS")
                    return

            # Check take profit
            if self.config.take_profit_pct:
                tp_price = self.position.entry_price * (1 + self.config.take_profit_pct)
                if high >= tp_price:
                    self._exit_position(date, tp_price, "TAKE_PROFIT")
                    return
        else:  # SHORT
            # Check stop loss
            if self.config.stop_loss_pct:
                sl_price = self.position.entry_price * (1 + self.config.stop_loss_pct)
                if high >= sl_price:
                    self._exit_position(date, sl_price, "STOP_LOSS")
                    return

            # Check take profit
            if self.config.take_profit_pct:
                tp_price = self.position.entry_price * (1 - self.config.take_profit_pct)
                if low <= tp_price:
                    self._exit_position(date, tp_price, "TAKE_PROFIT")
                    return

    def _record_equity(self, date: datetime, current_price: Decimal) -> None:
        """Record equity and drawdown at current point."""
        # Calculate current equity
        equity = self.capital
        if self.position:
            if self.position.side == "LONG":
                unrealized = (current_price - self.position.entry_price) * self.position.quantity
            else:
                unrealized = (self.position.entry_price - current_price) * self.position.quantity
            equity += unrealized

        # Update peak and drawdown
        if equity > self.peak_equity:
            self.peak_equity = equity

        drawdown = ((self.peak_equity - equity) / self.peak_equity) * 100
        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown

        self.equity_curve.append(
            {
                "date": date.isoformat() if hasattr(date, "isoformat") else str(date),
                "equity": float(equity),
            }
        )

    def _calculate_results(self, data: pd.DataFrame) -> BacktestResult:
        """Calculate final backtest results and metrics."""
        from app.modules.backtest.metrics import calculate_metrics

        metrics = calculate_metrics(
            trades=self.trades,
            equity_curve=self.equity_curve,
            initial_capital=self.config.initial_capital,
            final_capital=self.capital,
            start_date=self.config.start_date,
            end_date=self.config.end_date,
        )

        return BacktestResult(
            symbol=self.config.symbol,
            strategy_name=self.config.strategy.name,
            start_date=self.config.start_date,
            end_date=self.config.end_date,
            initial_capital=self.config.initial_capital,
            final_capital=self.capital,
            trades=self.trades,
            equity_curve=self.equity_curve,
            drawdown_curve=metrics.get("drawdown_curve", []),
            **metrics,
        )

"""Pydantic schemas for backtesting module."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator


class BacktestRequest(BaseModel):
    """Request schema for running a backtest."""

    symbol: str = Field(..., min_length=1, max_length=20, description="Symbol to backtest")
    strategy_name: str = Field(..., min_length=1, max_length=50, description="Strategy to use")
    start_date: datetime = Field(..., description="Backtest start date")
    end_date: datetime = Field(..., description="Backtest end date")
    initial_capital: Decimal = Field(
        default=Decimal("100000"), ge=Decimal("1000"), description="Initial capital"
    )
    timeframe: str = Field(default="1d", description="Data timeframe")
    strategy_params: dict[str, Any] | None = Field(
        default=None, description="Strategy-specific parameters"
    )

    @field_validator("symbol")
    @classmethod
    def uppercase_symbol(cls, v: str) -> str:
        return v.upper()

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, v: datetime, info) -> datetime:
        if "start_date" in info.data and v <= info.data["start_date"]:
            raise ValueError("end_date must be after start_date")
        return v


class BacktestTradeResponse(BaseModel):
    """Response schema for a single backtest trade."""

    id: str
    symbol: str
    side: str
    entry_date: datetime
    entry_price: Decimal
    exit_date: datetime | None
    exit_price: Decimal | None
    quantity: int
    pnl: Decimal | None
    pnl_pct: Decimal | None
    is_winner: bool | None
    exit_reason: str | None
    signal_indicators: dict[str, Any] | None

    class Config:
        from_attributes = True


class PerformanceMetrics(BaseModel):
    """Performance metrics for a backtest."""

    total_return: Decimal | None = Field(None, description="Total return percentage")
    annualized_return: Decimal | None = Field(None, description="Annualized return percentage")
    sharpe_ratio: Decimal | None = Field(None, description="Sharpe ratio (risk-adjusted return)")
    sortino_ratio: Decimal | None = Field(
        None, description="Sortino ratio (downside risk-adjusted)"
    )
    max_drawdown: Decimal | None = Field(None, description="Maximum drawdown percentage")
    calmar_ratio: Decimal | None = Field(None, description="Calmar ratio (return/max drawdown)")


class TradeStatistics(BaseModel):
    """Trade statistics for a backtest."""

    total_trades: int | None = Field(None, description="Total number of trades")
    winning_trades: int | None = Field(None, description="Number of winning trades")
    losing_trades: int | None = Field(None, description="Number of losing trades")
    win_rate: Decimal | None = Field(None, description="Win rate percentage")
    profit_factor: Decimal | None = Field(None, description="Gross profit / gross loss")
    avg_win: Decimal | None = Field(None, description="Average winning trade")
    avg_loss: Decimal | None = Field(None, description="Average losing trade")
    avg_trade: Decimal | None = Field(None, description="Average trade P&L")
    largest_win: Decimal | None = Field(None, description="Largest winning trade")
    largest_loss: Decimal | None = Field(None, description="Largest losing trade")


class EquityPoint(BaseModel):
    """Single point on the equity curve."""

    date: datetime
    equity: Decimal
    drawdown: Decimal | None = None


class BacktestResponse(BaseModel):
    """Response schema for a backtest result."""

    id: str
    user_id: str
    strategy_name: str
    symbol: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    initial_capital: Decimal
    final_capital: Decimal | None
    strategy_params: dict[str, Any] | None
    status: str
    error_message: str | None

    # Metrics
    performance: PerformanceMetrics
    trade_stats: TradeStatistics

    # Curves
    equity_curve: list[dict[str, Any]] | None
    drawdown_curve: list[dict[str, Any]] | None

    # Trades
    trades: list[BacktestTradeResponse] | None = None

    # Timestamps
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None

    class Config:
        from_attributes = True


class BacktestListResponse(BaseModel):
    """Response schema for listing backtests."""

    id: str
    strategy_name: str
    symbol: str
    status: str
    total_return: Decimal | None
    sharpe_ratio: Decimal | None
    total_trades: int | None
    win_rate: Decimal | None
    created_at: datetime
    completed_at: datetime | None

    class Config:
        from_attributes = True


class BacktestCompareRequest(BaseModel):
    """Request to compare multiple backtests."""

    backtest_ids: list[str] = Field(..., min_length=2, max_length=10)

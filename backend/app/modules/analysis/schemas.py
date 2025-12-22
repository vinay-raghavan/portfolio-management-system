"""Pydantic schemas for analysis module."""

from decimal import Decimal

from pydantic import BaseModel


class TechnicalIndicators(BaseModel):
    """Schema for technical indicators."""

    symbol: str
    # Moving Averages
    sma_20: Decimal | None = None
    sma_50: Decimal | None = None
    sma_200: Decimal | None = None
    ema_12: Decimal | None = None
    ema_26: Decimal | None = None
    # MACD
    macd: Decimal | None = None
    macd_signal: Decimal | None = None
    macd_histogram: Decimal | None = None
    # RSI
    rsi_14: Decimal | None = None
    # Bollinger Bands
    bb_upper: Decimal | None = None
    bb_middle: Decimal | None = None
    bb_lower: Decimal | None = None
    # Volatility
    atr_14: Decimal | None = None
    # Volume
    volume_sma_20: Decimal | None = None


class SignalStrength(BaseModel):
    """Schema for signal strength."""

    signal: str  # BUY, SELL, HOLD
    strength: Decimal  # 0-100
    confidence: Decimal  # 0-100


class AnalysisResult(BaseModel):
    """Schema for complete analysis result."""

    symbol: str
    current_price: Decimal
    indicators: TechnicalIndicators
    signal: SignalStrength
    support_levels: list[Decimal] = []
    resistance_levels: list[Decimal] = []
    trend: str  # BULLISH, BEARISH, NEUTRAL


class StockInfo(BaseModel):
    """Schema for detailed stock information."""

    symbol: str
    name: str | None = None
    exchange: str | None = None
    currency: str | None = None
    sector: str | None = None
    industry: str | None = None

    # Price info
    current_price: Decimal | None = None
    previous_close: Decimal | None = None
    open: Decimal | None = None
    day_high: Decimal | None = None
    day_low: Decimal | None = None

    # 52-week range
    week_52_high: Decimal | None = None
    week_52_low: Decimal | None = None

    # Volume
    volume: int | None = None
    avg_volume: int | None = None
    avg_volume_10d: int | None = None

    # Market cap and shares
    market_cap: Decimal | None = None
    shares_outstanding: int | None = None
    float_shares: int | None = None

    # Fundamentals
    pe_ratio: Decimal | None = None
    forward_pe: Decimal | None = None
    peg_ratio: Decimal | None = None
    price_to_book: Decimal | None = None
    eps: Decimal | None = None
    forward_eps: Decimal | None = None

    # Dividends
    dividend_yield: Decimal | None = None
    dividend_rate: Decimal | None = None
    ex_dividend_date: str | None = None

    # Analyst recommendations
    target_mean_price: Decimal | None = None
    target_high_price: Decimal | None = None
    target_low_price: Decimal | None = None
    recommendation: str | None = None
    num_analyst_opinions: int | None = None

    # Beta and other metrics
    beta: Decimal | None = None
    trailing_annual_return: Decimal | None = None


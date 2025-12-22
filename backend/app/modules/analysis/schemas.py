"""Pydantic schemas for analysis module."""

from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, PlainSerializer

# Custom type that serializes Decimal as float for JSON
DecimalAsFloat = Annotated[
    Decimal, PlainSerializer(lambda x: float(x) if x is not None else None, return_type=float)
]


class TechnicalIndicators(BaseModel):
    """Schema for technical indicators."""

    symbol: str
    # Moving Averages
    sma_20: DecimalAsFloat | None = None
    sma_50: DecimalAsFloat | None = None
    sma_200: DecimalAsFloat | None = None
    ema_12: DecimalAsFloat | None = None
    ema_26: DecimalAsFloat | None = None
    # MACD
    macd: DecimalAsFloat | None = None
    macd_signal: DecimalAsFloat | None = None
    macd_histogram: DecimalAsFloat | None = None
    # RSI
    rsi_14: DecimalAsFloat | None = None
    # Bollinger Bands
    bb_upper: DecimalAsFloat | None = None
    bb_middle: DecimalAsFloat | None = None
    bb_lower: DecimalAsFloat | None = None
    # Volatility
    atr_14: DecimalAsFloat | None = None
    # Volume
    volume_sma_20: DecimalAsFloat | None = None


class SignalStrength(BaseModel):
    """Schema for signal strength."""

    signal: str  # BUY, SELL, HOLD
    strength: DecimalAsFloat  # 0-100
    confidence: DecimalAsFloat  # 0-100


class AnalysisResult(BaseModel):
    """Schema for complete analysis result."""

    symbol: str
    current_price: DecimalAsFloat
    indicators: TechnicalIndicators
    signal: SignalStrength
    support_levels: list[DecimalAsFloat] = []
    resistance_levels: list[DecimalAsFloat] = []
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
    current_price: DecimalAsFloat | None = None
    previous_close: DecimalAsFloat | None = None
    open: DecimalAsFloat | None = None
    day_high: DecimalAsFloat | None = None
    day_low: DecimalAsFloat | None = None

    # 52-week range
    week_52_high: DecimalAsFloat | None = None
    week_52_low: DecimalAsFloat | None = None

    # Volume
    volume: int | None = None
    avg_volume: int | None = None
    avg_volume_10d: int | None = None

    # Market cap and shares
    market_cap: DecimalAsFloat | None = None
    shares_outstanding: int | None = None
    float_shares: int | None = None

    # Fundamentals
    pe_ratio: DecimalAsFloat | None = None
    forward_pe: DecimalAsFloat | None = None
    peg_ratio: DecimalAsFloat | None = None
    price_to_book: DecimalAsFloat | None = None
    eps: DecimalAsFloat | None = None
    forward_eps: DecimalAsFloat | None = None

    # Dividends
    dividend_yield: DecimalAsFloat | None = None
    dividend_rate: DecimalAsFloat | None = None
    ex_dividend_date: str | None = None

    # Analyst recommendations
    target_mean_price: DecimalAsFloat | None = None
    target_high_price: DecimalAsFloat | None = None
    target_low_price: DecimalAsFloat | None = None
    recommendation: str | None = None
    num_analyst_opinions: int | None = None

    # Beta and other metrics
    beta: DecimalAsFloat | None = None
    trailing_annual_return: DecimalAsFloat | None = None

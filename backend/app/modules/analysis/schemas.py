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


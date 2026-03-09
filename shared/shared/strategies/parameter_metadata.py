"""Strategy parameter metadata definitions.

This module provides comprehensive descriptions, units, and tuning guidance
for all strategy parameters. Used by the registry to populate tooltips in the UI.
"""

# Parameter metadata with description, unit, and tuning guidance
# Format: "param_name": {
#     "description": "What the parameter does",
#     "unit": "Unit of measurement (if applicable)",
#     "tuning": "How to adjust for different trading styles"
# }

PARAMETER_METADATA: dict[str, dict[str, str]] = {
    # ==================== COMMON PARAMETERS ====================
    "atr_period": {
        "description": "Number of periods for Average True Range calculation",
        "unit": "candles/bars",
        "tuning": "Lower (10-12) = more responsive stops. Higher (14-20) = smoother, fewer whipsaws",
    },
    "atr_multiplier": {
        "description": "Multiplier applied to ATR for stop loss distance",
        "unit": "× ATR",
        "tuning": "Lower (1.0-1.5) = tighter stops, more trades stopped out. "
        "Higher (2.0-3.0) = wider stops, more room for price movement",
    },
    "risk_reward_ratio": {
        "description": "Target profit distance as multiple of stop loss distance",
        "unit": "× risk",
        "tuning": "Lower (1.5) = higher win rate, smaller gains. "
        "Higher (2.5-3.0) = lower win rate, larger gains per trade",
    },
    # ==================== RSI STRATEGY ====================
    "rsi_period": {
        "description": "Number of periods for RSI (Relative Strength Index) calculation",
        "unit": "candles/bars",
        "tuning": "Lower (7-10) = more signals, more noise. "
        "Higher (14-21) = fewer signals, more reliable",
    },
    "oversold_threshold": {
        "description": "RSI level below which the stock is considered oversold (buy signal)",
        "unit": "RSI value (0-100)",
        "tuning": "Lower (20-25) = fewer but stronger signals. "
        "Higher (30-40) = more frequent signals",
    },
    "overbought_threshold": {
        "description": "RSI level above which the stock is considered overbought (sell signal)",
        "unit": "RSI value (0-100)",
        "tuning": "Higher (75-80) = fewer but stronger signals. "
        "Lower (65-70) = more frequent signals",
    },
    "rsi_threshold": {
        "description": "RSI centerline for bullish/bearish determination",
        "unit": "RSI value (0-100)",
        "tuning": "50 is standard. Higher (55) = require stronger momentum for buy",
    },
    # ==================== MACD STRATEGY ====================
    "fast_period": {
        "description": "Short-term EMA period for MACD or MA crossover",
        "unit": "candles/bars",
        "tuning": "Lower (8-10) = faster signals, more noise. "
        "Higher (12-15) = slower, smoother signals",
    },
    "slow_period": {
        "description": "Long-term EMA period for MACD or MA crossover",
        "unit": "candles/bars",
        "tuning": "Lower (20-22) = quicker crossovers. Higher (26-30) = filter out weak trends",
    },
    "signal_period": {
        "description": "Signal line EMA period (triggers the actual crossover)",
        "unit": "candles/bars",
        "tuning": "Lower (7-8) = earlier signals. Higher (9-12) = more confirmation",
    },
    # ==================== BOLLINGER BANDS ====================
    "bb_period": {
        "description": "Number of periods for Bollinger Bands middle line (SMA)",
        "unit": "candles/bars",
        "tuning": "Lower (10-15) = tighter bands, more touches. "
        "Higher (20-25) = wider bands, fewer signals",
    },
    "bb_std": {
        "description": "Number of standard deviations for upper/lower bands",
        "unit": "σ (std dev)",
        "tuning": "Lower (1.5-2.0) = narrower bands, more signals. "
        "Higher (2.0-2.5) = catch only extreme moves",
    },
    # ==================== MOVING AVERAGE ====================
    "ma_type": {
        "description": "Type of moving average to use",
        "unit": "ema or sma",
        "tuning": "EMA = more weight to recent prices, faster response. "
        "SMA = equal weight, smoother but lagging",
    },
    # ==================== EMA PERIODS ====================
    "ema_fast": {
        "description": "Fast EMA period for momentum scoring",
        "unit": "candles/bars",
        "tuning": "Lower (3-5) = very responsive. Higher (7-9) = smoother",
    },
    "ema_medium": {
        "description": "Medium EMA period for trend confirmation",
        "unit": "candles/bars",
        "tuning": "Should be 2-3× fast EMA. Common: 9, 13, 15",
    },
    "ema_slow": {
        "description": "Slow EMA period for overall trend direction",
        "unit": "candles/bars",
        "tuning": "Should be 2-4× medium EMA. Common: 21, 26, 34",
    },
    "ema_period": {
        "description": "EMA period for trend filter",
        "unit": "candles/bars",
        "tuning": "50 = medium-term trend. 20 = short-term. 200 = long-term",
    },
    # ==================== VOLUME PARAMETERS ====================
    "volume_lookback": {
        "description": "Number of periods for calculating average volume",
        "unit": "candles/bars",
        "tuning": "Lower (5-10) = recent volume focus. Higher (20-30) = more stable baseline",
    },
    "volume_multiplier": {
        "description": "Required volume as multiple of average for confirmation",
        "unit": "× avg volume",
        "tuning": "Lower (1.0-1.2) = accept normal volume. "
        "Higher (1.5-2.0) = require significant volume spike",
    },
    "volume_confirmation": {
        "description": "Minimum volume ratio vs average for valid signals",
        "unit": "× avg volume",
        "tuning": "1.0 = at least average. 1.5 = 50% above average required",
    },
    # ==================== VWAP STRATEGY ====================
    "band_std_dev": {
        "description": "Standard deviations for VWAP bands (similar to Bollinger)",
        "unit": "σ (std dev)",
        "tuning": "Lower (1.0-1.5) = tighter bands, more mean reversion trades. "
        "Higher (2.0-2.5) = only extreme deviations",
    },
    "entry_zone_pct": {
        "description": "Percentage of band width considered as entry zone",
        "unit": "% (0-1)",
        "tuning": "Lower (0.2) = must be very close to band. Higher (0.5) = broader entry area",
    },
    "trend_lookback": {
        "description": "Number of periods to assess trend direction",
        "unit": "candles/bars",
        "tuning": "Lower (10-15) = focus on recent trend. "
        "Higher (30-50) = consider broader context",
    },
    "min_trend_strength": {
        "description": "Minimum trend strength required (R² or slope metric)",
        "unit": "0-1 ratio",
        "tuning": "Lower (0.2) = trade in weak trends. "
        "Higher (0.5) = require strong directional move",
    },
    "require_band_touch": {
        "description": "Whether price must touch VWAP band before entry",
        "unit": "true/false",
        "tuning": "True = stricter entry, fewer trades. False = more trades",
    },
    "max_distance_from_vwap_pct": {
        "description": "Maximum allowed distance from VWAP to consider entry",
        "unit": "%",
        "tuning": "Lower (1-2%) = trade only near VWAP. Higher (3-5%) = allow extended moves",
    },
    "no_trade_after": {
        "description": "Time after which no new trades are initiated",
        "unit": "HH:MM (24h)",
        "tuning": "Earlier (11:00) = avoid afternoon volatility. "
        "Later (14:30) = trade most of the day",
    },
    # ==================== ORB STRATEGY ====================
    "range_minutes": {
        "description": "Duration of opening range to capture",
        "unit": "minutes",
        "tuning": "Lower (5-15) = tighter range, more breakouts. "
        "Higher (30-60) = wider range, fewer but larger moves",
    },
    "breakout_buffer_pct": {
        "description": "Buffer above/below range high/low to confirm breakout",
        "unit": "%",
        "tuning": "Lower (0.05-0.1%) = quicker entries. Higher (0.2-0.3%) = filter false breakouts",
    },
    "require_close_breakout": {
        "description": "Require candle close beyond range (vs just wick)",
        "unit": "true/false",
        "tuning": "True = more confirmation, fewer fakeouts. False = faster entry",
    },
    "stop_loss_method": {
        "description": "Method for calculating stop loss",
        "unit": "range, atr, or gap_midpoint",
        "tuning": "range = stop at opposite side. atr = ATR-based. "
        "gap_midpoint = middle of gap (for gap strategies)",
    },
    "stop_loss_pct": {
        "description": "Stop loss as percentage of entry price",
        "unit": "%",
        "tuning": "Lower (0.5-1%) = tight risk control. Higher (2-3%) = more room for volatility",
    },
    "max_entries_per_day": {
        "description": "Maximum number of entries allowed per trading day",
        "unit": "count",
        "tuning": "Lower (1-2) = selective, avoid overtrading. "
        "Higher (3-5) = capture more opportunities",
    },
    # ==================== GAP STRATEGY ====================
    "min_gap_pct": {
        "description": "Minimum gap size to consider trading",
        "unit": "%",
        "tuning": "Lower (0.5-1%) = trade smaller gaps. Higher (2-3%) = only significant gaps",
    },
    "max_gap_pct": {
        "description": "Maximum gap size (avoid extreme/news-driven gaps)",
        "unit": "%",
        "tuning": "Lower (5%) = conservative. Higher (8-10%) = trade bigger moves",
    },
    "require_confirmation": {
        "description": "Require price action confirmation before entry",
        "unit": "true/false",
        "tuning": "True = wait for follow-through. False = enter immediately",
    },
    "confirmation_candles": {
        "description": "Number of candles to wait for confirmation",
        "unit": "candles",
        "tuning": "Lower (1) = quick confirmation. Higher (2-3) = more patience",
    },
    "prefer_full_gaps": {
        "description": "Prioritize full gaps (gap beyond prior day's range)",
        "unit": "true/false",
        "tuning": "True = stronger setups only. False = trade partial gaps too",
    },
    "max_fill_target": {
        "description": "Use gap fill (prior close) as profit target",
        "unit": "true/false",
        "tuning": "True = conservative target. False = use R:R ratio instead",
    },
    # ==================== VWAP MOMENTUM ====================
    "buy_threshold": {
        "description": "Minimum score (out of 5) required for buy signal",
        "unit": "score (0-5)",
        "tuning": "Lower (2-3) = more signals. Higher (4) = require confluence",
    },
    "strong_buy_threshold": {
        "description": "Score for strong buy signal with higher confidence",
        "unit": "score (0-5)",
        "tuning": "Usually 4-5 for highest conviction entries",
    },
    "sell_threshold": {
        "description": "Score at or below which to generate sell signal",
        "unit": "score (0-5)",
        "tuning": "Higher (2) = sell earlier. Lower (1) = wait for extreme bearish",
    },
    "strong_sell_threshold": {
        "description": "Score for strong sell signal with higher confidence",
        "unit": "score (0-5)",
        "tuning": "Usually 0-1 for highest conviction exits/shorts",
    },
    # ==================== TWAP STRATEGY ====================
    "num_slices": {
        "description": "Number of execution slices for order splitting",
        "unit": "count",
        "tuning": "Lower (5-10) = fewer, larger orders. "
        "Higher (20-30) = more, smaller orders, less market impact",
    },
    "duration_minutes": {
        "description": "Total duration over which to execute the order",
        "unit": "minutes",
        "tuning": "Lower (30-60) = faster execution. Higher (120-240) = minimize market impact",
    },
    "randomize_pct": {
        "description": "Percentage to randomize slice timing (avoid detection)",
        "unit": "%",
        "tuning": "Lower (5-10%) = predictable. Higher (20-30%) = less detectable",
    },
    "min_slice_quantity": {
        "description": "Minimum quantity per slice",
        "unit": "shares",
        "tuning": "Set based on minimum lot size and liquidity",
    },
    # ==================== SWING STRATEGY ====================
    "swing_lookback": {
        "description": "Number of bars on each side to identify swing points",
        "unit": "candles/bars",
        "tuning": "Lower (3-5) = minor swings. Higher (7-10) = major swing points",
    },
    "require_trend_alignment": {
        "description": "Only trade in direction of the trend",
        "unit": "true/false",
        "tuning": "True = trend-following (safer). False = allow counter-trend",
    },
}


def get_parameter_description(param_name: str) -> str:
    """Get formatted description for a parameter.

    Args:
        param_name: Name of the parameter

    Returns:
        Formatted description string including unit and tuning guidance,
        or a title-cased version of the parameter name if not found.
    """
    meta = PARAMETER_METADATA.get(param_name)
    if not meta:
        # Fallback to title-cased parameter name
        return param_name.replace("_", " ").title()

    parts = [meta["description"]]
    if meta.get("unit"):
        parts.append(f"Unit: {meta['unit']}")
    if meta.get("tuning"):
        parts.append(f"Tuning: {meta['tuning']}")

    return " | ".join(parts)

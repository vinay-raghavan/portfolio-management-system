"""Technical analysis tasks."""

import logging

import yfinance as yf
from redis import Redis
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator, SMAIndicator
from ta.volatility import AverageTrueRange, BollingerBands

from worker.celery_app import celery_app
from worker.config import settings

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="worker.tasks.analysis.calculate_indicators")
def calculate_indicators(self, symbol: str) -> dict:
    """Calculate and cache technical indicators for a symbol."""
    logger.info(f"Calculating indicators for {symbol}")

    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="6mo")

        if hist.empty or len(hist) < 50:
            return {"status": "error", "message": "Insufficient data"}

        close = hist["Close"]
        high = hist["High"]
        low = hist["Low"]

        # Calculate indicators
        indicators = {
            "sma_20": float(SMAIndicator(close, window=20).sma_indicator().iloc[-1]),
            "sma_50": float(SMAIndicator(close, window=50).sma_indicator().iloc[-1]),
            "ema_12": float(EMAIndicator(close, window=12).ema_indicator().iloc[-1]),
            "ema_26": float(EMAIndicator(close, window=26).ema_indicator().iloc[-1]),
            "rsi_14": float(RSIIndicator(close, window=14).rsi().iloc[-1]),
        }

        # MACD
        macd_indicator = MACD(close)
        indicators["macd"] = float(macd_indicator.macd().iloc[-1])
        indicators["macd_signal"] = float(macd_indicator.macd_signal().iloc[-1])
        indicators["macd_histogram"] = float(macd_indicator.macd_diff().iloc[-1])

        # Bollinger Bands
        bb = BollingerBands(close, window=20, window_dev=2)
        indicators["bb_upper"] = float(bb.bollinger_hband().iloc[-1])
        indicators["bb_middle"] = float(bb.bollinger_mavg().iloc[-1])
        indicators["bb_lower"] = float(bb.bollinger_lband().iloc[-1])

        # ATR
        indicators["atr_14"] = float(
            AverageTrueRange(high, low, close, window=14).average_true_range().iloc[-1]
        )

        # Cache in Redis
        redis_client = Redis.from_url(settings.REDIS_URL)
        redis_client.hset(f"indicators:{symbol}", mapping=indicators)
        redis_client.expire(f"indicators:{symbol}", 300)  # 5 minutes

        logger.info(f"Indicators calculated for {symbol}")
        return {"status": "success", "symbol": symbol, "indicators": indicators}

    except Exception as e:
        logger.error(f"Error calculating indicators for {symbol}: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(bind=True, name="worker.tasks.analysis.calculate_daily_analytics")
def calculate_daily_analytics(self) -> dict:
    """Calculate daily analytics for all tracked symbols."""
    logger.info("Starting daily analytics calculation")

    redis_client = Redis.from_url(settings.REDIS_URL)
    symbols = redis_client.smembers("tracked_symbols")

    if not symbols:
        return {"status": "no_symbols", "processed": 0}

    processed = 0
    for symbol_bytes in symbols:
        symbol = symbol_bytes.decode("utf-8") if isinstance(symbol_bytes, bytes) else symbol_bytes
        try:
            calculate_indicators.delay(symbol)
            processed += 1
        except Exception as e:
            logger.error(f"Error queuing analytics for {symbol}: {e}")

    logger.info(f"Queued analytics for {processed} symbols")
    return {"status": "success", "processed": processed}

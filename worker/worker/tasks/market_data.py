"""Market data refresh tasks."""

import logging

import yfinance as yf
from redis import Redis

from worker.celery_app import celery_app
from worker.config import settings

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="worker.tasks.market_data.refresh_market_data")
def refresh_market_data(self) -> dict:
    """Refresh market data for tracked symbols."""
    logger.info("Starting market data refresh")

    redis_client = Redis.from_url(settings.REDIS_URL)

    # Get symbols to refresh from Redis set
    symbols = redis_client.smembers("tracked_symbols")

    if not symbols:
        logger.info("No symbols to refresh")
        return {"status": "no_symbols", "updated": 0}

    updated = 0
    for symbol_bytes in symbols:
        symbol = symbol_bytes.decode("utf-8") if isinstance(symbol_bytes, bytes) else symbol_bytes
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            price = info.get("regularMarketPrice") or info.get("currentPrice")
            if price:
                # Store in Redis with 5-minute TTL
                redis_client.setex(
                    f"price:{symbol}",
                    300,  # 5 minutes
                    str(price),
                )
                updated += 1
                logger.debug(f"Updated price for {symbol}: {price}")

        except Exception as e:
            logger.error(f"Error refreshing {symbol}: {e}")

    logger.info(f"Market data refresh complete. Updated {updated} symbols")
    return {"status": "success", "updated": updated}


@celery_app.task(bind=True, name="worker.tasks.market_data.fetch_historical_data")
def fetch_historical_data(self, symbol: str, period: str = "1y") -> dict:
    """Fetch and cache historical data for a symbol."""
    logger.info(f"Fetching historical data for {symbol}")

    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)

        if hist.empty:
            return {"status": "error", "message": "No data available"}

        # Convert to JSON-serializable format
        data = hist.reset_index().to_dict(orient="records")

        # Store in Redis with 1-hour TTL
        redis_client = Redis.from_url(settings.REDIS_URL)
        redis_client.setex(
            f"history:{symbol}:{period}",
            3600,  # 1 hour
            str(data),
        )

        return {"status": "success", "records": len(data)}

    except Exception as e:
        logger.error(f"Error fetching historical data for {symbol}: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(bind=True, name="worker.tasks.market_data.add_tracked_symbol")
def add_tracked_symbol(self, symbol: str) -> dict:
    """Add a symbol to the tracked symbols set."""
    redis_client = Redis.from_url(settings.REDIS_URL)
    redis_client.sadd("tracked_symbols", symbol.upper())
    logger.info(f"Added {symbol} to tracked symbols")
    return {"status": "success", "symbol": symbol.upper()}

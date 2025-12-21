"""Instrument master sync tasks.

This module provides Celery tasks for:
- Syncing NSE instrument master daily
- Syncing BSE instrument master daily
- Cleaning up expired instruments
"""

import csv
import io
import logging
from datetime import datetime, date
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from redis import Redis

from worker.celery_app import celery_app
from worker.config import settings

logger = logging.getLogger(__name__)

# Indian Standard Time
IST = ZoneInfo("Asia/Kolkata")

# NSE instrument master URLs
NSE_EQUITY_CSV_URL = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
NSE_FO_CSV_URL = "https://archives.nseindia.com/content/fo/fo_mktlots.csv"


def _get_http_client() -> httpx.Client:
    """Get HTTP client with proper headers."""
    return httpx.Client(
        timeout=60.0,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/csv,application/csv,text/plain,*/*",
        },
    )


@celery_app.task(bind=True, name="worker.tasks.instruments.sync_nse_equity_master")
def sync_nse_equity_master(self) -> dict:
    """Sync NSE equity instrument master.
    
    Downloads the equity list from NSE and stores in Redis for processing.
    The actual DB sync is done by the API service.
    """
    logger.info("Starting NSE equity master sync")
    
    try:
        client = _get_http_client()
        
        # First, visit NSE homepage to get cookies
        client.get("https://www.nseindia.com/")
        
        # Download equity CSV
        response = client.get(NSE_EQUITY_CSV_URL)
        response.raise_for_status()
        
        # Parse CSV
        content = response.text
        reader = csv.DictReader(io.StringIO(content))
        
        instruments = []
        for row in reader:
            try:
                instrument = {
                    "symbol": row.get("SYMBOL", "").strip(),
                    "name": row.get("NAME OF COMPANY", "").strip(),
                    "exchange": "NSE",
                    "segment": "EQ",
                    "instrument_type": "EQ",
                    "series": row.get("SERIES", "EQ").strip(),
                    "isin": row.get("ISIN NUMBER", "").strip(),
                    "lot_size": 1,
                    "tick_size": "0.05",
                    "is_active": True,
                    "is_tradeable": True,
                }
                if instrument["symbol"]:
                    instruments.append(instrument)
            except Exception as e:
                logger.warning(f"Error parsing row: {e}")
        
        # Store in Redis for API to process
        redis_client = Redis.from_url(settings.REDIS_URL)
        
        import json
        redis_client.setex(
            "instruments:nse:equity:pending",
            3600,  # 1 hour TTL
            json.dumps(instruments),
        )
        
        logger.info(f"NSE equity master sync complete. Found {len(instruments)} instruments")
        return {
            "status": "success",
            "exchange": "NSE",
            "segment": "EQ",
            "count": len(instruments),
        }
        
    except Exception as e:
        logger.error(f"Error syncing NSE equity master: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(bind=True, name="worker.tasks.instruments.sync_nse_indices")
def sync_nse_indices(self) -> dict:
    """Sync NSE index instruments."""
    logger.info("Starting NSE indices sync")

    # Pre-defined list of major NSE indices
    indices = [
        {"symbol": "NIFTY 50", "name": "Nifty 50", "exchange": "NSE", "instrument_type": "IDX"},
        {"symbol": "NIFTY BANK", "name": "Nifty Bank", "exchange": "NSE", "instrument_type": "IDX"},
        {"symbol": "NIFTY IT", "name": "Nifty IT", "exchange": "NSE", "instrument_type": "IDX"},
        {"symbol": "NIFTY NEXT 50", "name": "Nifty Next 50", "exchange": "NSE", "instrument_type": "IDX"},
        {"symbol": "NIFTY MIDCAP 50", "name": "Nifty Midcap 50", "exchange": "NSE", "instrument_type": "IDX"},
        {"symbol": "NIFTY INFRA", "name": "Nifty Infrastructure", "exchange": "NSE", "instrument_type": "IDX"},
        {"symbol": "NIFTY REALTY", "name": "Nifty Realty", "exchange": "NSE", "instrument_type": "IDX"},
        {"symbol": "NIFTY ENERGY", "name": "Nifty Energy", "exchange": "NSE", "instrument_type": "IDX"},
        {"symbol": "NIFTY FMCG", "name": "Nifty FMCG", "exchange": "NSE", "instrument_type": "IDX"},
        {"symbol": "NIFTY MNC", "name": "Nifty MNC", "exchange": "NSE", "instrument_type": "IDX"},
        {"symbol": "NIFTY PHARMA", "name": "Nifty Pharma", "exchange": "NSE", "instrument_type": "IDX"},
        {"symbol": "NIFTY PSE", "name": "Nifty PSE", "exchange": "NSE", "instrument_type": "IDX"},
        {"symbol": "NIFTY PSU BANK", "name": "Nifty PSU Bank", "exchange": "NSE", "instrument_type": "IDX"},
        {"symbol": "NIFTY AUTO", "name": "Nifty Auto", "exchange": "NSE", "instrument_type": "IDX"},
        {"symbol": "NIFTY MEDIA", "name": "Nifty Media", "exchange": "NSE", "instrument_type": "IDX"},
        {"symbol": "NIFTY METAL", "name": "Nifty Metal", "exchange": "NSE", "instrument_type": "IDX"},
        {"symbol": "NIFTY FIN SERVICE", "name": "Nifty Financial Services", "exchange": "NSE", "instrument_type": "IDX"},
    ]

    # Add common fields
    for idx in indices:
        idx.update({
            "segment": "IDX",
            "lot_size": 1,
            "tick_size": "0.05",
            "is_active": True,
            "is_tradeable": False,  # Indices are not directly tradeable
        })

    # Store in Redis
    redis_client = Redis.from_url(settings.REDIS_URL)
    import json
    redis_client.setex(
        "instruments:nse:indices:pending",
        3600,
        json.dumps(indices),
    )

    logger.info(f"NSE indices sync complete. Found {len(indices)} indices")
    return {"status": "success", "exchange": "NSE", "segment": "IDX", "count": len(indices)}


@celery_app.task(bind=True, name="worker.tasks.instruments.sync_nse_fo_master")
def sync_nse_fo_master(self) -> dict:
    """Sync NSE F&O instrument master with lot sizes.

    Downloads the F&O lot size data from NSE and stores in Redis.
    """
    logger.info("Starting NSE F&O master sync")

    try:
        client = _get_http_client()

        # First, visit NSE homepage to get cookies
        client.get("https://www.nseindia.com/")

        # Download F&O lot size CSV
        response = client.get(NSE_FO_CSV_URL)
        response.raise_for_status()

        # Parse CSV - F&O lot size format is different
        content = response.text
        lines = content.strip().split('\n')

        instruments = []
        # Skip header rows (usually first 2 lines)
        for line in lines[2:]:
            try:
                parts = line.split(',')
                if len(parts) >= 2:
                    symbol = parts[0].strip()
                    # Lot sizes are in subsequent columns for different expiries
                    lot_size = int(parts[1].strip()) if parts[1].strip().isdigit() else 1

                    if symbol and symbol != "SYMBOL":
                        instrument = {
                            "symbol": symbol,
                            "name": symbol,
                            "exchange": "NSE",
                            "segment": "FO",
                            "instrument_type": "FUT",
                            "lot_size": lot_size,
                            "tick_size": "0.05",
                            "is_active": True,
                            "is_tradeable": True,
                        }
                        instruments.append(instrument)
            except Exception as e:
                logger.warning(f"Error parsing F&O row: {e}")

        # Store in Redis for API to process
        redis_client = Redis.from_url(settings.REDIS_URL)

        import json
        redis_client.setex(
            "instruments:nse:fo:pending",
            3600,  # 1 hour TTL
            json.dumps(instruments),
        )

        logger.info(f"NSE F&O master sync complete. Found {len(instruments)} instruments")
        return {
            "status": "success",
            "exchange": "NSE",
            "segment": "FO",
            "count": len(instruments),
        }

    except Exception as e:
        logger.error(f"Error syncing NSE F&O master: {e}")
        return {"status": "error", "message": str(e)}


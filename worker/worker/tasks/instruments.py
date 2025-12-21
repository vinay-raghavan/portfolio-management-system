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


@celery_app.task(bind=True, name="worker.tasks.instruments.sync_instruments_weekly")
def sync_instruments_weekly(self) -> dict:
    """Weekly sync of all NSE instruments via API endpoints.

    This task:
    1. Syncs Nifty 500 constituents (with industry data)
    2. Syncs all NSE stocks from equity master CSV

    Runs every Sunday at 6 AM IST (00:30 UTC).
    """
    import time

    logger.info("Starting weekly instrument master sync")

    # Use internal API URL
    api_url = "http://api:8000/api/v1/instruments"

    results = {
        "nifty500": None,
        "all_nse": None,
        "status": "success",
    }

    try:
        client = httpx.Client(timeout=120.0)

        # Step 1: Sync Nifty 500 for industry data
        logger.info("Syncing Nifty 500 constituents...")
        try:
            response = client.post(f"{api_url}/sync/nifty/NIFTY500")
            if response.status_code == 200:
                results["nifty500"] = response.json()
                logger.info(f"Nifty 500 sync: {results['nifty500']}")
            else:
                results["nifty500"] = {"error": response.text}
                logger.warning(f"Nifty 500 sync failed: {response.status_code}")
        except Exception as e:
            results["nifty500"] = {"error": str(e)}
            logger.error(f"Error syncing Nifty 500: {e}")

        # Small delay between requests
        time.sleep(2)

        # Step 2: Sync all NSE stocks
        logger.info("Syncing all NSE stocks...")
        try:
            response = client.post(f"{api_url}/sync/nse/all")
            if response.status_code == 200:
                results["all_nse"] = response.json()
                logger.info(f"All NSE sync: {results['all_nse']}")
            else:
                results["all_nse"] = {"error": response.text}
                logger.warning(f"All NSE sync failed: {response.status_code}")
        except Exception as e:
            results["all_nse"] = {"error": str(e)}
            logger.error(f"Error syncing all NSE: {e}")

        client.close()

        logger.info("Weekly instrument master sync complete")
        return results

    except Exception as e:
        logger.error(f"Error in weekly instrument sync: {e}")
        return {"status": "error", "message": str(e)}

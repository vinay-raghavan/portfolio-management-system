"""Universe service for algo trading.

Manages symbol universes for strategy trading.
"""

import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.algo.models import Universe
from app.modules.algo.schemas import UniverseCreate, UniverseUpdate
from app.modules.instruments.models import Instrument

logger = logging.getLogger(__name__)

# Predefined universe definitions
PREDEFINED_UNIVERSES = {
    "NIFTY50": {
        "name": "Nifty 50",
        "description": "Top 50 companies by market cap on NSE",
        "symbols": [
            "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
            "HINDUNILVR", "SBIN", "BHARTIARTL", "ITC", "KOTAKBANK",
            "LT", "AXISBANK", "ASIANPAINT", "MARUTI", "HCLTECH",
            "SUNPHARMA", "TITAN", "BAJFINANCE", "WIPRO", "ULTRACEMCO",
            "NESTLEIND", "NTPC", "POWERGRID", "ONGC", "M&M",
            "TATAMOTORS", "JSWSTEEL", "TATASTEEL", "ADANIENT", "ADANIPORTS",
            "COALINDIA", "BAJAJFINSV", "TECHM", "INDUSINDBK", "HINDALCO",
            "DRREDDY", "DIVISLAB", "CIPLA", "GRASIM", "BRITANNIA",
            "APOLLOHOSP", "EICHERMOT", "HEROMOTOCO", "BPCL", "TATACONSUM",
            "SBILIFE", "HDFCLIFE", "UPL", "BAJAJ-AUTO", "LTIM",
        ],
    },
    "BANKNIFTY": {
        "name": "Bank Nifty",
        "description": "Major banking stocks in Nifty Bank index",
        "symbols": [
            "HDFCBANK", "ICICIBANK", "SBIN", "KOTAKBANK", "AXISBANK",
            "INDUSINDBK", "BANDHANBNK", "FEDERALBNK", "IDFCFIRSTB", "PNB",
            "BANKBARODA", "AUBANK",
        ],
    },
    "NIFTYNEXT50": {
        "name": "Nifty Next 50",
        "description": "Next 50 companies after Nifty 50",
        "symbols": [
            "ADANIGREEN", "AMBUJACEM", "AUROPHARMA", "BAJAJHLDNG", "BERGEPAINT",
            "BIOCON", "BOSCHLTD", "CHOLAFIN", "COLPAL", "DABUR",
            "DLF", "GAIL", "GODREJCP", "HAVELLS", "ICICIPRULI",
            "ICICIGI", "INDUSTOWER", "IOC", "IRCTC", "JINDALSTEL",
            "LICI", "LUPIN", "MARICO", "MCDOWELL-N", "MUTHOOTFIN",
            "NAUKRI", "NHPC", "NMDC", "PAGEIND", "PGHH",
            "PIDILITIND", "PFC", "RECLTD", "SAIL", "SBICARD",
            "SHREECEM", "SIEMENS", "SRF", "TATAPOWER", "TORNTPHARM",
            "TRENT", "VEDL", "VBL", "YESBANK", "ZOMATO",
            "ZYDUSLIFE", "ABB", "ATGL", "CANBK", "DMART",
        ],
    },
    "NIFTYIT": {
        "name": "Nifty IT",
        "description": "IT sector stocks",
        "symbols": [
            "TCS", "INFY", "HCLTECH", "WIPRO", "TECHM",
            "LTIM", "MPHASIS", "COFORGE", "PERSISTENT", "LTTS",
        ],
    },
    "NIFTYPHARMA": {
        "name": "Nifty Pharma",
        "description": "Pharmaceutical sector stocks",
        "symbols": [
            "SUNPHARMA", "DRREDDY", "DIVISLAB", "CIPLA", "APOLLOHOSP",
            "AUROPHARMA", "BIOCON", "LUPIN", "TORNTPHARM", "ZYDUSLIFE",
        ],
    },
}


class UniverseService:
    """Service for managing trading universes."""

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db

    async def create(self, user_id: str, data: UniverseCreate) -> Universe:
        """Create a new custom universe."""
        universe = Universe(
            user_id=user_id,
            name=data.name,
            description=data.description,
            symbols=data.symbols,
            filter_criteria=data.filter_criteria,
            is_dynamic=data.is_dynamic,
            is_system=False,
        )
        self.db.add(universe)
        await self.db.flush()
        await self.db.refresh(universe)
        logger.info(f"Created universe {universe.id}: {universe.name}")
        return universe

    async def get_by_id(self, universe_id: str) -> Universe | None:
        """Get universe by ID."""
        result = await self.db.execute(select(Universe).where(Universe.id == universe_id))
        return result.scalar_one_or_none()

    async def get_user_universes(self, user_id: str) -> list[Universe]:
        """Get all universes accessible to a user (own + system)."""
        result = await self.db.execute(
            select(Universe).where(
                (Universe.user_id == user_id) | (Universe.is_system == True)  # noqa: E712
            )
        )
        return list(result.scalars().all())

    async def get_system_universes(self) -> list[Universe]:
        """Get all system universes."""
        result = await self.db.execute(
            select(Universe).where(Universe.is_system == True)  # noqa: E712
        )
        return list(result.scalars().all())

    async def update(
        self, user_id: str, universe_id: str, data: UniverseUpdate
    ) -> Universe | None:
        """Update a universe (only user's own universes)."""
        result = await self.db.execute(
            select(Universe).where(
                Universe.id == universe_id,
                Universe.user_id == user_id,
            )
        )
        universe = result.scalar_one_or_none()

        if not universe:
            return None

        if data.name is not None:
            universe.name = data.name
        if data.description is not None:
            universe.description = data.description
        if data.symbols is not None:
            universe.symbols = data.symbols
        if data.filter_criteria is not None:
            universe.filter_criteria = data.filter_criteria

        await self.db.flush()
        await self.db.refresh(universe)
        return universe

    async def delete(self, user_id: str, universe_id: str) -> bool:
        """Delete a universe (only user's own universes)."""
        result = await self.db.execute(
            select(Universe).where(
                Universe.id == universe_id,
                Universe.user_id == user_id,
            )
        )
        universe = result.scalar_one_or_none()

        if not universe:
            return False

        await self.db.delete(universe)
        await self.db.flush()
        return True

    async def resolve_symbols(self, universe: Universe) -> list[str]:
        """Resolve the actual symbols for a universe.

        For static universes, returns the symbols list.
        For dynamic universes, applies filter criteria to instruments.
        """
        if not universe.is_dynamic:
            return universe.symbols or []

        # Dynamic universe - apply filters
        return await self._apply_dynamic_filters(universe.filter_criteria or {})

    async def _apply_dynamic_filters(self, criteria: dict) -> list[str]:
        """Apply dynamic filter criteria to get symbols.

        Supported criteria:
        - exchange: Filter by exchange (NSE, BSE)
        - segment: Filter by segment (EQ, FO)
        - sector: Filter by sector
        - min_lot_size: Minimum lot size (for F&O)
        - is_tradeable: Only tradeable instruments
        - limit: Maximum number of symbols
        """
        query = select(Instrument).where(Instrument.is_active == True)  # noqa: E712

        if criteria.get("exchange"):
            query = query.where(Instrument.exchange == criteria["exchange"])

        if criteria.get("segment"):
            query = query.where(Instrument.segment == criteria["segment"])

        if criteria.get("sector"):
            query = query.where(Instrument.sector == criteria["sector"])

        if criteria.get("instrument_type"):
            query = query.where(Instrument.instrument_type == criteria["instrument_type"])

        if criteria.get("is_tradeable", True):
            query = query.where(Instrument.is_tradeable == True)  # noqa: E712

        if criteria.get("min_lot_size"):
            query = query.where(Instrument.lot_size >= criteria["min_lot_size"])

        limit = criteria.get("limit", 100)
        query = query.limit(limit)

        result = await self.db.execute(query)
        instruments = result.scalars().all()

        return [inst.symbol for inst in instruments]

    async def seed_predefined_universes(self) -> int:
        """Seed predefined system universes.

        Returns number of universes created.
        """
        created = 0

        for key, definition in PREDEFINED_UNIVERSES.items():
            # Check if already exists
            result = await self.db.execute(
                select(Universe).where(
                    Universe.name == definition["name"],
                    Universe.is_system == True,  # noqa: E712
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update symbols if changed
                if existing.symbols != definition["symbols"]:
                    existing.symbols = definition["symbols"]
                    existing.description = definition["description"]
                continue

            # Create new system universe
            universe = Universe(
                user_id=None,
                name=definition["name"],
                description=definition["description"],
                symbols=definition["symbols"],
                is_system=True,
                is_dynamic=False,
            )
            self.db.add(universe)
            created += 1
            logger.info(f"Created system universe: {definition['name']}")

        await self.db.flush()
        return created

    async def get_fo_stocks(self) -> list[str]:
        """Get all F&O eligible stocks from instruments."""
        result = await self.db.execute(
            select(Instrument.symbol).where(
                Instrument.segment == "FO",
                Instrument.instrument_type == "FUT",
                Instrument.is_active == True,  # noqa: E712
            ).distinct()
        )
        return [row[0] for row in result.all()]

    async def create_fo_universe(self) -> Universe:
        """Create or update F&O stocks universe."""
        fo_symbols = await self.get_fo_stocks()

        # Check if exists
        result = await self.db.execute(
            select(Universe).where(
                Universe.name == "F&O Stocks",
                Universe.is_system == True,  # noqa: E712
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.symbols = fo_symbols
            await self.db.flush()
            return existing

        universe = Universe(
            user_id=None,
            name="F&O Stocks",
            description="All F&O eligible stocks on NSE",
            symbols=fo_symbols,
            is_system=True,
            is_dynamic=True,
            filter_criteria={"segment": "FO", "instrument_type": "FUT"},
        )
        self.db.add(universe)
        await self.db.flush()
        await self.db.refresh(universe)
        return universe


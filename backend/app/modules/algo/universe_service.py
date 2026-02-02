"""Universe service for algo trading.

Manages symbol universes for strategy trading.
"""

import logging
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.algo.models import Universe
from app.modules.algo.schemas import UniverseCreate, UniverseUpdate
from app.modules.instruments.models import Instrument

if TYPE_CHECKING:
    from app.providers.data.nse import NSEDataProvider

logger = logging.getLogger(__name__)

# Predefined universe definitions
PREDEFINED_UNIVERSES = {
    "NIFTY50": {
        "name": "Nifty 50",
        "description": "Top 50 companies by market cap on NSE",
        "symbols": [
            "RELIANCE",
            "TCS",
            "HDFCBANK",
            "INFY",
            "ICICIBANK",
            "HINDUNILVR",
            "SBIN",
            "BHARTIARTL",
            "ITC",
            "KOTAKBANK",
            "LT",
            "AXISBANK",
            "ASIANPAINT",
            "MARUTI",
            "HCLTECH",
            "SUNPHARMA",
            "TITAN",
            "BAJFINANCE",
            "WIPRO",
            "ULTRACEMCO",
            "NESTLEIND",
            "NTPC",
            "POWERGRID",
            "ONGC",
            "M&M",
            "TATAMOTORS",
            "JSWSTEEL",
            "TATASTEEL",
            "ADANIENT",
            "ADANIPORTS",
            "COALINDIA",
            "BAJAJFINSV",
            "TECHM",
            "INDUSINDBK",
            "HINDALCO",
            "DRREDDY",
            "DIVISLAB",
            "CIPLA",
            "GRASIM",
            "BRITANNIA",
            "APOLLOHOSP",
            "EICHERMOT",
            "HEROMOTOCO",
            "BPCL",
            "TATACONSUM",
            "SBILIFE",
            "HDFCLIFE",
            "UPL",
            "BAJAJ-AUTO",
            "LTIM",
        ],
    },
    "BANKNIFTY": {
        "name": "Bank Nifty",
        "description": "Major banking stocks in Nifty Bank index",
        "symbols": [
            "HDFCBANK",
            "ICICIBANK",
            "SBIN",
            "KOTAKBANK",
            "AXISBANK",
            "INDUSINDBK",
            "BANDHANBNK",
            "FEDERALBNK",
            "IDFCFIRSTB",
            "PNB",
            "BANKBARODA",
            "AUBANK",
        ],
    },
    "NIFTYNEXT50": {
        "name": "Nifty Next 50",
        "description": "Next 50 companies after Nifty 50",
        "symbols": [
            "ADANIGREEN",
            "AMBUJACEM",
            "AUROPHARMA",
            "BAJAJHLDNG",
            "BERGEPAINT",
            "BIOCON",
            "BOSCHLTD",
            "CHOLAFIN",
            "COLPAL",
            "DABUR",
            "DLF",
            "GAIL",
            "GODREJCP",
            "HAVELLS",
            "ICICIPRULI",
            "ICICIGI",
            "INDUSTOWER",
            "IOC",
            "IRCTC",
            "JINDALSTEL",
            "LICI",
            "LUPIN",
            "MARICO",
            "MCDOWELL-N",
            "MUTHOOTFIN",
            "NAUKRI",
            "NHPC",
            "NMDC",
            "PAGEIND",
            "PGHH",
            "PIDILITIND",
            "PFC",
            "RECLTD",
            "SAIL",
            "SBICARD",
            "SHREECEM",
            "SIEMENS",
            "SRF",
            "TATAPOWER",
            "TORNTPHARM",
            "TRENT",
            "VEDL",
            "VBL",
            "YESBANK",
            "ZOMATO",
            "ZYDUSLIFE",
            "ABB",
            "ATGL",
            "CANBK",
            "DMART",
        ],
    },
    "NIFTYIT": {
        "name": "Nifty IT",
        "description": "IT sector stocks",
        "symbols": [
            "TCS",
            "INFY",
            "HCLTECH",
            "WIPRO",
            "TECHM",
            "LTIM",
            "MPHASIS",
            "COFORGE",
            "PERSISTENT",
            "LTTS",
        ],
    },
    "NIFTYPHARMA": {
        "name": "Nifty Pharma",
        "description": "Pharmaceutical sector stocks",
        "symbols": [
            "SUNPHARMA",
            "DRREDDY",
            "DIVISLAB",
            "CIPLA",
            "APOLLOHOSP",
            "AUROPHARMA",
            "BIOCON",
            "LUPIN",
            "TORNTPHARM",
            "ZYDUSLIFE",
        ],
    },
    "NIFTYAUTO": {
        "name": "Nifty Auto",
        "description": "Automobile sector stocks",
        "symbols": [
            "TATAMOTORS",
            "M&M",
            "MARUTI",
            "BAJAJ-AUTO",
            "HEROMOTOCO",
            "EICHERMOT",
            "TVSMOTOR",
            "ASHOKLEY",
            "BALKRISIND",
            "BHARATFORG",
            "BOSCHLTD",
            "MOTHERSON",
            "MRF",
            "EXIDEIND",
            "APOLLOTYRE",
        ],
    },
    "NIFTYFMCG": {
        "name": "Nifty FMCG",
        "description": "Fast Moving Consumer Goods stocks",
        "symbols": [
            "HINDUNILVR",
            "ITC",
            "NESTLEIND",
            "BRITANNIA",
            "TATACONSUM",
            "DABUR",
            "MARICO",
            "GODREJCP",
            "COLPAL",
            "VBL",
            "UBL",
            "MCDOWELL-N",
            "PGHH",
            "EMAMILTD",
            "RADICO",
        ],
    },
    "NIFTYMETAL": {
        "name": "Nifty Metal",
        "description": "Metal and mining sector stocks",
        "symbols": [
            "TATASTEEL",
            "JSWSTEEL",
            "HINDALCO",
            "COALINDIA",
            "VEDL",
            "JINDALSTEL",
            "SAIL",
            "NMDC",
            "NATIONALUM",
            "APLAPOLLO",
            "RATNAMANI",
            "WELCORP",
            "HINDCOPPER",
            "MOIL",
            "HINDZINC",
        ],
    },
    "NIFTYENERGY": {
        "name": "Nifty Energy",
        "description": "Energy sector stocks",
        "symbols": [
            "RELIANCE",
            "ONGC",
            "NTPC",
            "POWERGRID",
            "BPCL",
            "IOC",
            "GAIL",
            "ADANIGREEN",
            "TATAPOWER",
            "ADANIPORTS",
        ],
    },
    "NIFTYREALTY": {
        "name": "Nifty Realty",
        "description": "Real estate sector stocks",
        "symbols": [
            "DLF",
            "GODREJPROP",
            "PRESTIGE",
            "OBEROIRLTY",
            "BRIGADE",
            "PHOENIXLTD",
            "SOBHA",
            "SUNTECK",
            "MAHLIFE",
            "LODHA",
        ],
    },
    "NIFTYPSU": {
        "name": "Nifty PSU Bank",
        "description": "Public Sector Bank stocks",
        "symbols": [
            "SBIN",
            "BANKBARODA",
            "PNB",
            "CANBK",
            "UNIONBANK",
            "IOB",
            "INDIANB",
            "CENTRALBK",
            "MAHABANK",
            "BANKINDIA",
            "UCOBANK",
            "PSB",
        ],
    },
}

# Dynamic universes fetched from NSE
DYNAMIC_UNIVERSES = {
    "NIFTY500": {
        "name": "Nifty 500",
        "description": "Top 500 companies by market cap on NSE (dynamically updated)",
        "nse_index": "NIFTY 500",
    },
    "NIFTY100": {
        "name": "Nifty 100",
        "description": "Top 100 companies by market cap on NSE",
        "nse_index": "NIFTY 100",
    },
    "NIFTY200": {
        "name": "Nifty 200",
        "description": "Top 200 companies by market cap on NSE",
        "nse_index": "NIFTY 200",
    },
    "NIFTYMIDCAP50": {
        "name": "Nifty Midcap 50",
        "description": "Top 50 midcap companies on NSE",
        "nse_index": "NIFTY MIDCAP 50",
    },
    "NIFTYMIDCAP100": {
        "name": "Nifty Midcap 100",
        "description": "Top 100 midcap companies on NSE",
        "nse_index": "NIFTY MIDCAP 100",
    },
    "NIFTYMIDCAP150": {
        "name": "Nifty Midcap 150",
        "description": "Top 150 midcap companies on NSE",
        "nse_index": "NIFTY MIDCAP 150",
    },
    "NIFTYSMALLCAP50": {
        "name": "Nifty Smallcap 50",
        "description": "Top 50 smallcap companies on NSE",
        "nse_index": "NIFTY SMLCAP 50",
    },
    "NIFTYSMALLCAP100": {
        "name": "Nifty Smallcap 100",
        "description": "Top 100 smallcap companies on NSE",
        "nse_index": "NIFTY SMLCAP 100",
    },
    "NIFTYSMALLCAP250": {
        "name": "Nifty Smallcap 250",
        "description": "Top 250 smallcap companies on NSE",
        "nse_index": "NIFTY SMLCAP 250",
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

    async def update(self, user_id: str, universe_id: str, data: UniverseUpdate) -> Universe | None:
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

        for _key, definition in PREDEFINED_UNIVERSES.items():
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
            select(Instrument.symbol)
            .where(
                Instrument.segment == "FO",
                Instrument.instrument_type == "FUT",
                Instrument.is_active == True,  # noqa: E712
            )
            .distinct()
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

    async def fetch_index_symbols(
        self, nse_index: str, nse_provider: "NSEDataProvider"
    ) -> list[str]:
        """Fetch symbols for an NSE index.

        Args:
            nse_index: NSE index name (e.g., "NIFTY 500")
            nse_provider: NSE data provider instance

        Returns:
            List of symbols in the index
        """
        constituents = await nse_provider.get_index_constituents(nse_index)
        return [c["symbol"] for c in constituents if c.get("symbol")]

    async def create_or_update_dynamic_universe(
        self,
        key: str,
        nse_provider: "NSEDataProvider",
    ) -> Universe | None:
        """Create or update a dynamic universe from NSE index.

        Args:
            key: Key from DYNAMIC_UNIVERSES
            nse_provider: NSE data provider instance

        Returns:
            Created/updated universe or None if failed
        """
        if key not in DYNAMIC_UNIVERSES:
            logger.warning(f"Unknown dynamic universe key: {key}")
            return None

        definition = DYNAMIC_UNIVERSES[key]
        nse_index = definition["nse_index"]

        # Fetch symbols from NSE
        symbols = await self.fetch_index_symbols(nse_index, nse_provider)
        if not symbols:
            logger.warning(f"No symbols fetched for {nse_index}")
            return None

        # Check if exists
        result = await self.db.execute(
            select(Universe).where(
                Universe.name == definition["name"],
                Universe.is_system == True,  # noqa: E712
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.symbols = symbols
            existing.description = f"{definition['description']} ({len(symbols)} stocks)"
            await self.db.flush()
            logger.info(
                f"Updated dynamic universe: {definition['name']} with {len(symbols)} symbols"
            )
            return existing

        # Create new
        universe = Universe(
            user_id=None,
            name=definition["name"],
            description=f"{definition['description']} ({len(symbols)} stocks)",
            symbols=symbols,
            is_system=True,
            is_dynamic=True,
            filter_criteria={"nse_index": nse_index},
        )
        self.db.add(universe)
        await self.db.flush()
        await self.db.refresh(universe)
        logger.info(f"Created dynamic universe: {definition['name']} with {len(symbols)} symbols")
        return universe

    async def seed_dynamic_universes(self, nse_provider: "NSEDataProvider") -> int:
        """Seed all dynamic universes from NSE.

        Args:
            nse_provider: NSE data provider instance

        Returns:
            Number of universes created/updated
        """
        count = 0
        for key in DYNAMIC_UNIVERSES:
            try:
                universe = await self.create_or_update_dynamic_universe(key, nse_provider)
                if universe:
                    count += 1
            except Exception as e:
                logger.error(f"Error creating dynamic universe {key}: {e}")
        return count

    async def get_all_nse_stocks(self) -> list[str]:
        """Get all tradeable NSE equity stocks from instruments table.

        Returns:
            List of all NSE equity symbols
        """
        result = await self.db.execute(
            select(Instrument.symbol)
            .where(
                Instrument.exchange == "NSE",
                Instrument.segment == "EQ",
                Instrument.instrument_type == "EQ",
                Instrument.is_active == True,  # noqa: E712
                Instrument.is_tradeable == True,  # noqa: E712
            )
            .distinct()
            .order_by(Instrument.symbol)
        )
        return [row[0] for row in result.all()]

    async def create_all_nse_universe(self) -> Universe:
        """Create or update the 'All NSE Stocks' universe.

        This is a large universe containing all tradeable NSE equity stocks.
        Should be used with screeners to filter down to tradeable candidates.

        Returns:
            The All NSE Stocks universe
        """
        symbols = await self.get_all_nse_stocks()

        # Check if exists
        result = await self.db.execute(
            select(Universe).where(
                Universe.name == "All NSE Stocks",
                Universe.is_system == True,  # noqa: E712
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.symbols = symbols
            existing.description = f"All tradeable NSE equity stocks ({len(symbols)} stocks)"
            await self.db.flush()
            logger.info(f"Updated All NSE Stocks universe with {len(symbols)} symbols")
            return existing

        universe = Universe(
            user_id=None,
            name="All NSE Stocks",
            description=f"All tradeable NSE equity stocks ({len(symbols)} stocks)",
            symbols=symbols,
            is_system=True,
            is_dynamic=True,
            filter_criteria={"exchange": "NSE", "segment": "EQ", "is_tradeable": True},
        )
        self.db.add(universe)
        await self.db.flush()
        await self.db.refresh(universe)
        logger.info(f"Created All NSE Stocks universe with {len(symbols)} symbols")
        return universe

    @staticmethod
    def get_available_universes() -> dict:
        """Get all available universe definitions (static + dynamic).

        Returns:
            Dictionary of universe definitions
        """
        all_universes = {}

        # Add static universes
        for key, definition in PREDEFINED_UNIVERSES.items():
            all_universes[key] = {
                **definition,
                "type": "static",
                "count": len(definition.get("symbols", [])),
            }

        # Add dynamic universes
        for key, definition in DYNAMIC_UNIVERSES.items():
            all_universes[key] = {
                **definition,
                "type": "dynamic",
                "count": None,  # Unknown until fetched
            }

        # Add special universes
        all_universes["ALL_NSE"] = {
            "name": "All NSE Stocks",
            "description": "All tradeable NSE equity stocks (2200+)",
            "type": "dynamic",
            "count": None,
        }
        all_universes["FO_STOCKS"] = {
            "name": "F&O Stocks",
            "description": "All F&O eligible stocks on NSE (~200)",
            "type": "dynamic",
            "count": None,
        }

        return all_universes

"""Instrument service for CRUD and search operations."""

import logging
from datetime import datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.instruments.models import Instrument
from app.modules.instruments.schemas import (
    InstrumentBulkResponse,
    InstrumentCreate,
    InstrumentSearchParams,
)

logger = logging.getLogger(__name__)


class InstrumentService:
    """Service for instrument operations."""

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db

    async def create(self, data: InstrumentCreate) -> Instrument:
        """Create a new instrument."""
        instrument = Instrument(**data.model_dump())
        self.db.add(instrument)
        await self.db.flush()
        await self.db.refresh(instrument)
        return instrument

    async def get_by_id(self, instrument_id: str) -> Instrument | None:
        """Get instrument by ID."""
        result = await self.db.execute(select(Instrument).where(Instrument.id == instrument_id))
        return result.scalar_one_or_none()

    async def get_by_symbol(self, symbol: str, exchange: str | None = None) -> Instrument | None:
        """Get instrument by symbol and optionally exchange."""
        query = select(Instrument).where(
            Instrument.symbol == symbol.upper(),
            Instrument.is_active,
        )
        if exchange:
            query = query.where(Instrument.exchange == exchange.upper())

        result = await self.db.execute(query.limit(1))
        return result.scalar_one_or_none()

    async def search(self, params: InstrumentSearchParams) -> tuple[list[Instrument], int]:
        """Search instruments with filters.

        Returns:
            Tuple of (results, total_count)
        """
        # Base query
        query = select(Instrument)
        count_query = select(func.count(Instrument.id))

        # Apply filters
        filters = []

        if params.query:
            search_term = f"%{params.query.upper()}%"
            filters.append(
                or_(
                    Instrument.symbol.ilike(search_term),
                    Instrument.name.ilike(search_term),
                )
            )

        if params.exchange:
            filters.append(Instrument.exchange == params.exchange.upper())

        if params.segment:
            filters.append(Instrument.segment == params.segment.upper())

        if params.instrument_type:
            filters.append(Instrument.instrument_type == params.instrument_type.upper())

        if params.is_active is not None:
            filters.append(Instrument.is_active == params.is_active)

        if params.underlying:
            filters.append(Instrument.underlying == params.underlying.upper())

        if params.expiry_from:
            filters.append(Instrument.expiry >= params.expiry_from)

        if params.expiry_to:
            filters.append(Instrument.expiry <= params.expiry_to)

        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        # Get total count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination and ordering
        query = query.order_by(Instrument.symbol).offset(params.offset).limit(params.limit)

        result = await self.db.execute(query)
        instruments = list(result.scalars().all())

        return instruments, total

    async def get_by_exchange(
        self, exchange: str, segment: str | None = None, limit: int = 100
    ) -> list[Instrument]:
        """Get instruments for an exchange."""
        query = select(Instrument).where(
            Instrument.exchange == exchange.upper(),
            Instrument.is_active,
        )
        if segment:
            query = query.where(Instrument.segment == segment.upper())

        result = await self.db.execute(query.limit(limit))
        return list(result.scalars().all())

    async def upsert_bulk(self, instruments: list[InstrumentCreate]) -> InstrumentBulkResponse:
        """Bulk upsert instruments (create or update).

        Uses symbol + exchange + expiry as unique key.
        """
        created = 0
        updated = 0
        failed = 0
        errors: list[str] = []

        for data in instruments:
            try:
                # Check if exists
                query = select(Instrument).where(
                    Instrument.symbol == data.symbol.upper(),
                    Instrument.exchange == data.exchange.upper(),
                )
                if data.expiry:
                    query = query.where(Instrument.expiry == data.expiry)
                else:
                    query = query.where(Instrument.expiry.is_(None))

                result = await self.db.execute(query)
                existing = result.scalar_one_or_none()

                if existing:
                    # Update existing
                    for key, value in data.model_dump(exclude_unset=True).items():
                        setattr(existing, key, value)
                    existing.last_synced_at = datetime.utcnow()
                    updated += 1
                else:
                    # Create new
                    instrument = Instrument(**data.model_dump())
                    instrument.last_synced_at = datetime.utcnow()
                    self.db.add(instrument)
                    created += 1

            except Exception as e:
                failed += 1
                errors.append(f"{data.symbol}: {str(e)}")
                logger.error(f"Failed to upsert {data.symbol}: {e}")

        await self.db.flush()

        return InstrumentBulkResponse(
            created=created,
            updated=updated,
            failed=failed,
            errors=errors[:10],  # Limit errors to first 10
        )

    async def deactivate_old_instruments(self, exchange: str, synced_before: datetime) -> int:
        """Deactivate instruments not synced recently.

        Args:
            exchange: Exchange to filter
            synced_before: Deactivate if last_synced_at is before this time

        Returns:
            Number of deactivated instruments
        """
        query = select(Instrument).where(
            Instrument.exchange == exchange.upper(),
            Instrument.is_active,
            or_(
                Instrument.last_synced_at < synced_before,
                Instrument.last_synced_at.is_(None),
            ),
        )

        result = await self.db.execute(query)
        instruments = result.scalars().all()

        count = 0
        for instrument in instruments:
            instrument.is_active = False
            count += 1

        await self.db.flush()
        return count

    async def get_indices(self, exchange: str = "NSE") -> list[Instrument]:
        """Get all index instruments."""
        result = await self.db.execute(
            select(Instrument).where(
                Instrument.exchange == exchange.upper(),
                Instrument.instrument_type == "IDX",
                Instrument.is_active,
            )
        )
        return list(result.scalars().all())

    async def get_fo_underlyings(self, exchange: str = "NSE") -> list[str]:
        """Get unique underlyings for F&O instruments."""
        result = await self.db.execute(
            select(Instrument.underlying)
            .where(
                Instrument.exchange == exchange.upper(),
                Instrument.segment == "FO",
                Instrument.underlying.isnot(None),
                Instrument.is_active,
            )
            .distinct()
        )
        return [row[0] for row in result.all() if row[0]]

    async def get_expiry_dates(self, underlying: str, exchange: str = "NSE") -> list:
        """Get available expiry dates for an underlying."""
        from datetime import date

        result = await self.db.execute(
            select(Instrument.expiry)
            .where(
                Instrument.underlying == underlying.upper(),
                Instrument.exchange == exchange.upper(),
                Instrument.expiry >= date.today(),
                Instrument.is_active,
            )
            .distinct()
            .order_by(Instrument.expiry)
        )
        return [row[0] for row in result.all() if row[0]]

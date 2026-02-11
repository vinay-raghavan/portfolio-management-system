"""Daily digest generation service."""

import logging
from datetime import date, datetime
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from shared.providers.data.base import DataProvider
from shared.providers.data.yahoo import YahooDataProvider
from shared.providers.news import BaseNewsProvider, get_news_provider
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import DailyDigest
from .schemas import (
    BreakoutCandidate,
    DailyDigestResponse,
    IndexPerformance,
    MarketSummary,
    NewsHighlight,
    SectorDigest,
    TopMover,
    VolumeLeader,
)

logger = logging.getLogger(__name__)

# Indian market timezone
IST = ZoneInfo("Asia/Kolkata")

# Major indices to track
INDICES = [
    ("^NSEI", "NIFTY 50"),
    ("^NSEBANK", "NIFTY BANK"),
    ("^BSESN", "SENSEX"),
]


class DigestService:
    """Service for generating and retrieving daily market digests."""

    def __init__(
        self,
        db: AsyncSession,
        provider: DataProvider | None = None,
        news_provider: BaseNewsProvider | None = None,
    ):
        """Initialize digest service.

        Args:
            db: Database session
            provider: Data provider for quotes. Defaults to YahooDataProvider.
            news_provider: News provider. Defaults to factory default.
        """
        self.db = db
        self.provider = provider or YahooDataProvider()
        self.news_provider = news_provider or get_news_provider()

    async def get_latest_digest(self) -> DailyDigest | None:
        """Get the most recent daily digest."""
        result = await self.db.execute(
            select(DailyDigest).order_by(desc(DailyDigest.digest_date)).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_digest_by_date(self, target_date: date) -> DailyDigest | None:
        """Get digest for a specific date."""
        # Convert date to datetime at start of day in IST
        start_of_day = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=IST)
        end_of_day = datetime.combine(target_date, datetime.max.time()).replace(tzinfo=IST)

        result = await self.db.execute(
            select(DailyDigest).where(
                DailyDigest.digest_date >= start_of_day,
                DailyDigest.digest_date <= end_of_day,
            )
        )
        return result.scalar_one_or_none()

    async def get_digests(self, limit: int = 10, offset: int = 0) -> tuple[list[DailyDigest], int]:
        """Get paginated list of digests."""
        # Get total count
        count_result = await self.db.execute(select(DailyDigest.id))
        total = len(count_result.all())

        # Get digests
        result = await self.db.execute(
            select(DailyDigest).order_by(desc(DailyDigest.digest_date)).offset(offset).limit(limit)
        )
        digests = list(result.scalars().all())

        return digests, total

    async def generate_digest(self, target_date: date | None = None) -> DailyDigest:
        """Generate a daily digest for the given date.

        Args:
            target_date: Date to generate digest for. Defaults to today.

        Returns:
            Created DailyDigest model instance
        """
        import asyncio

        if target_date is None:
            target_date = date.today()

        digest_datetime = datetime.combine(target_date, datetime.now(IST).time()).replace(
            tzinfo=IST
        )

        logger.info(f"Generating daily digest for {target_date}")

        # Fetch all data concurrently
        tasks = [
            self._fetch_market_summary(),
            self._fetch_top_movers(),
            self._fetch_sector_performance(),
            self._fetch_volume_leaders(),
            self._fetch_breakout_candidates(),
            self._fetch_news_highlights(),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Parse results
        market_summary = results[0] if not isinstance(results[0], Exception) else {}
        gainers, losers = results[1] if not isinstance(results[1], Exception) else ([], [])
        sector_perf = results[2] if not isinstance(results[2], Exception) else {}
        volume_leaders = results[3] if not isinstance(results[3], Exception) else []
        breakouts = results[4] if not isinstance(results[4], Exception) else []
        news = results[5] if not isinstance(results[5], Exception) else []

        # Calculate overall sentiment from news
        sentiment = self._calculate_market_sentiment(news)

        # Create digest record
        # Use mode="json" to ensure datetime fields are serialized to ISO strings
        digest = DailyDigest(
            id=str(uuid4()),
            digest_date=digest_datetime,
            market_summary=market_summary,
            top_gainers=[g.model_dump(mode="json") for g in gainers],
            top_losers=[loser.model_dump(mode="json") for loser in losers],
            sector_performance=sector_perf,
            volume_leaders=[v.model_dump(mode="json") for v in volume_leaders],
            breakout_candidates=[b.model_dump(mode="json") for b in breakouts],
            news_highlights=[n.model_dump(mode="json") for n in news],
            market_sentiment=sentiment,
        )

        self.db.add(digest)
        await self.db.flush()

        logger.info(f"Generated digest {digest.id} for {target_date}")
        return digest

    async def _fetch_market_summary(self) -> dict[str, Any]:
        """Fetch major index performance."""
        import asyncio

        async def fetch_index(symbol: str, name: str) -> IndexPerformance | None:
            try:
                quote = await self.provider.get_quote(symbol)
                if quote:
                    return IndexPerformance(
                        symbol=symbol,
                        name=name,
                        close=float(quote.last_price) if quote.last_price else None,
                        change=float(quote.change) if quote.change else None,
                        change_pct=float(quote.change_pct) if quote.change_pct else None,
                    )
            except Exception as e:
                logger.warning(f"Failed to fetch index {symbol}: {e}")
            return None

        results = await asyncio.gather(
            *[fetch_index(symbol, name) for symbol, name in INDICES],
            return_exceptions=True,
        )

        indices = [r for r in results if isinstance(r, IndexPerformance)]

        # Determine overall trend
        if indices:
            avg_change = sum((i.change_pct or 0) for i in indices) / len(indices)
            if avg_change > 0.5:
                trend = "bullish"
            elif avg_change < -0.5:
                trend = "bearish"
            else:
                trend = "neutral"
        else:
            trend = "unknown"

        return {
            "indices": [i.model_dump() for i in indices],
            "overall_trend": trend,
            "trading_date": datetime.now(IST).isoformat(),
        }

    async def _fetch_top_movers(self, limit: int = 10) -> tuple[list[TopMover], list[TopMover]]:
        """Fetch top gainers and losers from Nifty 500."""
        try:
            # Import NSE provider for index constituents
            from shared.providers.data.nse import NSEDataProvider

            nse = NSEDataProvider()
            constituents = await nse.get_index_constituents("NIFTY 500")

            if not constituents:
                logger.warning("No constituents data from NSE")
                return [], []

            # Sort by change percentage
            stocks = [
                TopMover(
                    symbol=c.get("symbol", ""),
                    name=c.get("name") or c.get("companyName"),
                    close=c.get("lastPrice"),
                    change_pct=c.get("pChange", 0),
                    volume=c.get("totalTradedVolume"),
                )
                for c in constituents
                if c.get("symbol") and c.get("pChange") is not None
            ]

            # Sort for gainers (highest change) and losers (lowest change)
            gainers = sorted(stocks, key=lambda x: x.change_pct, reverse=True)[:limit]
            losers = sorted(stocks, key=lambda x: x.change_pct)[:limit]

            return gainers, losers
        except Exception as e:
            logger.error(f"Error fetching top movers: {e}")
            return [], []

    async def _fetch_sector_performance(self) -> dict[str, Any]:
        """Fetch sector-wise performance."""
        try:
            from shared.providers.data.nse import NSEDataProvider

            nse = NSEDataProvider()
            constituents = await nse.get_index_constituents("NIFTY 500")

            if not constituents:
                return {}

            # Group by industry/sector
            sectors: dict[str, list[dict]] = {}
            for c in constituents:
                sector = c.get("industry") or c.get("sector") or "Other"
                if sector not in sectors:
                    sectors[sector] = []
                sectors[sector].append(c)

            # Calculate average change per sector
            sector_data = []
            for sector, stocks in sectors.items():
                changes = [s.get("pChange", 0) for s in stocks if s.get("pChange") is not None]
                if changes:
                    avg_change = sum(changes) / len(changes)
                    top_stock = max(stocks, key=lambda s: s.get("pChange", 0))
                    sector_data.append(
                        SectorDigest(
                            sector=sector,
                            change_pct=round(avg_change, 2),
                            top_stock=top_stock.get("symbol"),
                            stock_count=len(stocks),
                        )
                    )

            # Sort by performance
            sector_data.sort(key=lambda x: x.change_pct or 0, reverse=True)

            return {"sectors": [s.model_dump() for s in sector_data]}
        except Exception as e:
            logger.error(f"Error fetching sector performance: {e}")
            return {}

    async def _fetch_volume_leaders(self, limit: int = 10) -> list[VolumeLeader]:
        """Fetch stocks with unusual volume activity."""
        try:
            from shared.providers.data.nse import NSEDataProvider

            nse = NSEDataProvider()
            constituents = await nse.get_index_constituents("NIFTY 500")

            if not constituents:
                return []

            # Calculate volume ratio (current volume / average volume)
            leaders = []
            for c in constituents:
                volume = c.get("totalTradedVolume")
                avg_volume = c.get("averageVolume")  # May not be available

                if volume and volume > 0:
                    # Use a heuristic if avg_volume not available
                    volume_ratio = None
                    if avg_volume and avg_volume > 0:
                        volume_ratio = round(volume / avg_volume, 2)

                    leaders.append(
                        VolumeLeader(
                            symbol=c.get("symbol", ""),
                            name=c.get("name") or c.get("companyName"),
                            volume=int(volume),
                            avg_volume=int(avg_volume) if avg_volume else None,
                            volume_ratio=volume_ratio,
                            price_change_pct=c.get("pChange"),
                        )
                    )

            # Sort by volume (highest first)
            leaders.sort(key=lambda x: x.volume, reverse=True)
            return leaders[:limit]
        except Exception as e:
            logger.error(f"Error fetching volume leaders: {e}")
            return []

    async def _fetch_breakout_candidates(self, limit: int = 10) -> list[BreakoutCandidate]:
        """Fetch stocks showing breakout patterns.

        Uses the breakout screener to find candidates.
        """
        try:
            from shared.providers.data.nse import NSEDataProvider

            from app.modules.screener.screener import StockScreener

            nse = NSEDataProvider()
            constituents = await nse.get_index_constituents("NIFTY 200")

            if not constituents:
                return []

            symbols = [c.get("symbol") for c in constituents if c.get("symbol")]

            # Create breakout screener
            screener = StockScreener.create_breakout_screener(data_provider=self.provider)
            results = await screener.screen_universe(symbols=symbols, min_score=60, top_n=limit)

            candidates = []
            for r in results:
                if r.passed:
                    candidates.append(
                        BreakoutCandidate(
                            symbol=r.symbol,
                            pattern="Breakout",
                            strength=r.score,
                        )
                    )

            return candidates
        except Exception as e:
            logger.error(f"Error fetching breakout candidates: {e}")
            return []

    async def _fetch_news_highlights(self, limit: int = 5) -> list[NewsHighlight]:
        """Fetch top market news with sentiment."""
        try:
            news_response = await self.news_provider.get_market_news(limit=limit)

            highlights = []
            for article in news_response.articles:
                highlights.append(
                    NewsHighlight(
                        title=article.title,
                        source=article.source,
                        url=article.url,
                        published_at=article.published_at,
                        sentiment=article.sentiment.value if article.sentiment else None,
                        related_symbols=article.related_symbols or [],
                    )
                )

            return highlights
        except Exception as e:
            logger.error(f"Error fetching news highlights: {e}")
            return []

    def _calculate_market_sentiment(self, news: list[NewsHighlight]) -> float | None:
        """Calculate overall market sentiment from news.

        Returns:
            Sentiment score from -1.0 (bearish) to 1.0 (bullish)
        """
        if not news:
            return None

        sentiment_values = {
            "positive": 1.0,
            "negative": -1.0,
            "neutral": 0.0,
        }

        scores = []
        for n in news:
            if n.sentiment and n.sentiment in sentiment_values:
                scores.append(sentiment_values[n.sentiment])

        if not scores:
            return None

        return round(sum(scores) / len(scores), 3)

    def digest_to_response(self, digest: DailyDigest) -> DailyDigestResponse:
        """Convert DailyDigest model to response schema."""
        return DailyDigestResponse(
            id=digest.id,
            digest_date=digest.digest_date,
            market_summary=MarketSummary(
                indices=[
                    IndexPerformance(**idx)
                    for idx in (digest.market_summary or {}).get("indices", [])
                ],
                overall_trend=(digest.market_summary or {}).get("overall_trend"),
                trading_date=digest.digest_date,
            )
            if digest.market_summary
            else None,
            top_gainers=[TopMover(**g) for g in (digest.top_gainers or [])],
            top_losers=[TopMover(**loser) for loser in (digest.top_losers or [])],
            sector_performance=[
                SectorDigest(**s) for s in (digest.sector_performance or {}).get("sectors", [])
            ],
            volume_leaders=[VolumeLeader(**v) for v in (digest.volume_leaders or [])],
            breakout_candidates=[
                BreakoutCandidate(**b) for b in (digest.breakout_candidates or [])
            ],
            news_highlights=[NewsHighlight(**n) for n in (digest.news_highlights or [])],
            market_sentiment=float(digest.market_sentiment) if digest.market_sentiment else None,
            created_at=digest.created_at,
        )

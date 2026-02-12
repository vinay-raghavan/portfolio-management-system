"""Tests for research digest module."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.research.digest_service import DigestService
from app.modules.research.models import DailyDigest
from app.modules.research.schemas import (
    BreakoutCandidate,
    DailyDigestResponse,
    DigestListResponse,
    IndexPerformance,
    MarketSummary,
    NewsHighlight,
    SectorDigest,
    TopMover,
    VolumeLeader,
)


class TestDigestSchemas:
    """Tests for digest Pydantic schemas."""

    def test_index_performance_minimal(self):
        """Test IndexPerformance with minimal fields."""
        perf = IndexPerformance(symbol="^NSEI")
        assert perf.symbol == "^NSEI"
        assert perf.name is None
        assert perf.close is None

    def test_index_performance_full(self):
        """Test IndexPerformance with all fields."""
        perf = IndexPerformance(
            symbol="^NSEI",
            name="NIFTY 50",
            close=22000.50,
            change=150.25,
            change_pct=0.69,
        )
        assert perf.name == "NIFTY 50"
        assert perf.close == 22000.50
        assert perf.change_pct == 0.69

    def test_top_mover(self):
        """Test TopMover schema."""
        mover = TopMover(
            symbol="RELIANCE",
            name="Reliance Industries",
            close=2500.0,
            change_pct=5.5,
            volume=10000000,
            reason="Q3 results",
        )
        assert mover.symbol == "RELIANCE"
        assert mover.change_pct == 5.5

    def test_sector_digest(self):
        """Test SectorDigest schema."""
        sector = SectorDigest(
            sector="IT",
            change_pct=2.5,
            top_stock="TCS",
            stock_count=15,
        )
        assert sector.sector == "IT"
        assert sector.top_stock == "TCS"

    def test_volume_leader(self):
        """Test VolumeLeader schema."""
        leader = VolumeLeader(
            symbol="TATAMOTORS",
            name="Tata Motors",
            volume=50000000,
            avg_volume=10000000,
            volume_ratio=5.0,
            price_change_pct=3.2,
        )
        assert leader.volume == 50000000
        assert leader.volume_ratio == 5.0

    def test_breakout_candidate(self):
        """Test BreakoutCandidate schema."""
        candidate = BreakoutCandidate(
            symbol="INFY",
            name="Infosys",
            pattern="52-week high",
            current_price=1800.0,
            breakout_level=1750.0,
            strength=85.0,
        )
        assert candidate.pattern == "52-week high"
        assert candidate.strength == 85.0

    def test_news_highlight(self):
        """Test NewsHighlight schema."""
        highlight = NewsHighlight(
            title="Market hits new high",
            source="Reuters",
            url="https://example.com/news",
            sentiment="positive",
            related_symbols=["TCS", "INFY"],
        )
        assert highlight.title == "Market hits new high"
        assert highlight.sentiment == "positive"
        assert len(highlight.related_symbols) == 2

    def test_daily_digest_response(self):
        """Test DailyDigestResponse schema."""
        now = datetime.now(UTC)
        digest = DailyDigestResponse(
            id="test-id",
            digest_date=now,
            market_summary=MarketSummary(
                indices=[IndexPerformance(symbol="^NSEI", change_pct=0.5)],
                overall_trend="bullish",
            ),
            top_gainers=[TopMover(symbol="RELIANCE", change_pct=5.0)],
            top_losers=[TopMover(symbol="HDFC", change_pct=-3.0)],
            market_sentiment=0.65,
            created_at=now,
        )
        assert digest.id == "test-id"
        assert digest.market_sentiment == 0.65
        assert len(digest.top_gainers) == 1

    def test_digest_list_response(self):
        """Test DigestListResponse schema."""
        response = DigestListResponse(
            digests=[],
            total_count=0,
        )
        assert response.total_count == 0
        assert len(response.digests) == 0


class TestDigestServiceMethods:
    """Tests for DigestService internal methods."""

    def test_calculate_market_sentiment_positive(self):
        """Test sentiment calculation with positive news."""
        mock_db = MagicMock()
        service = DigestService(db=mock_db)

        news = [
            NewsHighlight(title="Market rallies", sentiment="positive"),
            NewsHighlight(title="Stocks gain", sentiment="positive"),
            NewsHighlight(title="Flat trading", sentiment="neutral"),
        ]

        sentiment = service._calculate_market_sentiment(news)
        assert sentiment is not None
        assert sentiment > 0  # Should be positive

    def test_calculate_market_sentiment_negative(self):
        """Test sentiment calculation with negative news."""
        mock_db = MagicMock()
        service = DigestService(db=mock_db)

        news = [
            NewsHighlight(title="Market crashes", sentiment="negative"),
            NewsHighlight(title="Stocks fall", sentiment="negative"),
        ]

        sentiment = service._calculate_market_sentiment(news)
        assert sentiment is not None
        assert sentiment < 0  # Should be negative

    def test_calculate_market_sentiment_empty(self):
        """Test sentiment calculation with no news."""
        mock_db = MagicMock()
        service = DigestService(db=mock_db)

        sentiment = service._calculate_market_sentiment([])
        assert sentiment is None

    def test_calculate_market_sentiment_neutral(self):
        """Test sentiment calculation with mixed news."""
        mock_db = MagicMock()
        service = DigestService(db=mock_db)

        news = [
            NewsHighlight(title="Market rallies", sentiment="positive"),
            NewsHighlight(title="Market falls", sentiment="negative"),
        ]

        sentiment = service._calculate_market_sentiment(news)
        assert sentiment is not None
        assert sentiment == 0.0  # Should be neutral


class TestDigestServiceDatabase:
    """Tests for DigestService database operations."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = AsyncMock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        """Create DigestService with mocked dependencies."""
        return DigestService(db=mock_db)

    @pytest.mark.asyncio
    async def test_get_latest_digest(self, service, mock_db):
        """Test getting the latest digest."""
        now = datetime.now(UTC)
        mock_digest = DailyDigest(
            id="test-id",
            digest_date=now,
            market_summary={},
            created_at=now,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_digest
        mock_db.execute.return_value = mock_result

        result = await service.get_latest_digest()

        assert result is not None
        assert result.id == "test-id"

    @pytest.mark.asyncio
    async def test_get_latest_digest_none(self, service, mock_db):
        """Test getting latest digest when none exists."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.get_latest_digest()

        assert result is None

    @pytest.mark.asyncio
    async def test_get_digests_paginated(self, service, mock_db):
        """Test getting paginated digests."""
        now = datetime.now(UTC)
        mock_digests = [
            DailyDigest(id="1", digest_date=now, created_at=now),
            DailyDigest(id="2", digest_date=now, created_at=now),
        ]

        # Mock count query
        mock_count_result = MagicMock()
        mock_count_result.all.return_value = [("1",), ("2",)]

        # Mock list query
        mock_list_result = MagicMock()
        mock_list_result.scalars.return_value.all.return_value = mock_digests

        mock_db.execute.side_effect = [mock_count_result, mock_list_result]

        digests, total = await service.get_digests(limit=10, offset=0)

        assert total == 2
        assert len(digests) == 2

    def test_digest_to_response(self, service):
        """Test converting DailyDigest model to response."""
        now = datetime.now(UTC)
        digest = DailyDigest(
            id="test-id",
            digest_date=now,
            market_summary={
                "indices": [{"symbol": "^NSEI", "change_pct": 0.5}],
                "overall_trend": "bullish",
            },
            top_gainers=[{"symbol": "RELIANCE", "change_pct": 5.0}],
            top_losers=[{"symbol": "HDFC", "change_pct": -3.0}],
            sector_performance={"sectors": [{"sector": "IT", "change_pct": 2.0}]},
            volume_leaders=[{"symbol": "TATA", "volume": 1000000}],
            breakout_candidates=[{"symbol": "INFY", "pattern": "Breakout"}],
            news_highlights=[{"title": "News", "sentiment": "positive"}],
            market_sentiment=0.5,
            created_at=now,
        )

        response = service.digest_to_response(digest)

        assert response.id == "test-id"
        assert response.market_summary is not None
        assert response.market_summary.overall_trend == "bullish"
        assert len(response.top_gainers) == 1
        assert len(response.top_losers) == 1
        assert len(response.sector_performance) == 1
        assert response.market_sentiment == 0.5

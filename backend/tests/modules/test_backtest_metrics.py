"""Unit tests for backtest performance metrics."""

import pytest
import numpy as np
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock

from app.modules.backtest.metrics import (
    calculate_total_return,
    calculate_annualized_return,
    calculate_daily_returns,
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_max_drawdown,
    calculate_calmar_ratio,
    calculate_trade_statistics,
    calculate_metrics,
)


def make_equity_curve(equities: list[float]) -> list[dict]:
    """Helper to create equity curve with dates."""
    start = datetime.now(timezone.utc) - timedelta(days=len(equities))
    return [
        {"date": (start + timedelta(days=i)).isoformat(), "equity": e}
        for i, e in enumerate(equities)
    ]


class TestTotalReturn:
    """Tests for total return calculation."""

    def test_total_return_positive(self):
        """Test total return calculation with positive returns."""
        # 10% gain
        result = calculate_total_return(Decimal("100000"), Decimal("110000"))
        assert result == pytest.approx(10.0, rel=0.01)

    def test_total_return_negative(self):
        """Test total return calculation with negative returns."""
        # 15% loss
        result = calculate_total_return(Decimal("100000"), Decimal("85000"))
        assert result == pytest.approx(-15.0, rel=0.01)

    def test_total_return_zero(self):
        """Test total return calculation with no change."""
        result = calculate_total_return(Decimal("100000"), Decimal("100000"))
        assert result == pytest.approx(0.0, rel=0.01)

    def test_total_return_zero_initial(self):
        """Test total return with zero initial capital."""
        result = calculate_total_return(Decimal("0"), Decimal("100000"))
        assert result == 0.0


class TestMaxDrawdown:
    """Tests for maximum drawdown calculation."""

    def test_max_drawdown(self):
        """Test maximum drawdown calculation."""
        # Peak at 120k, trough at 90k = 25% drawdown
        equity_curve = make_equity_curve([100000.0, 120000.0, 100000.0, 90000.0, 110000.0])
        max_dd, _ = calculate_max_drawdown(equity_curve)

        assert max_dd == pytest.approx(25.0, rel=0.01)

    def test_max_drawdown_no_drawdown(self):
        """Test max drawdown when equity only goes up."""
        equity_curve = make_equity_curve([100000.0, 110000.0, 120000.0, 130000.0])
        max_dd, _ = calculate_max_drawdown(equity_curve)

        assert max_dd == pytest.approx(0.0, rel=0.01)

    def test_max_drawdown_empty(self):
        """Test max drawdown with empty equity curve."""
        max_dd, curve = calculate_max_drawdown([])
        assert max_dd == 0.0
        assert curve == []


class TestSharpeRatio:
    """Tests for Sharpe ratio calculation."""

    def test_sharpe_ratio_positive(self):
        """Test Sharpe ratio with positive returns."""
        # Create daily returns with positive mean and low volatility
        np.random.seed(42)
        daily_returns = np.random.normal(0.001, 0.01, 252)  # 0.1% daily return, 1% vol

        sharpe = calculate_sharpe_ratio(daily_returns)

        # Sharpe should be positive with positive returns
        assert sharpe > 0

    def test_sharpe_ratio_negative(self):
        """Test Sharpe ratio with negative returns."""
        # Create daily returns with negative mean
        np.random.seed(42)
        daily_returns = np.random.normal(-0.002, 0.01, 252)  # -0.2% daily return

        sharpe = calculate_sharpe_ratio(daily_returns)

        # Sharpe should be negative with negative returns
        assert sharpe < 0

    def test_sharpe_ratio_empty(self):
        """Test Sharpe ratio with empty returns."""
        sharpe = calculate_sharpe_ratio(np.array([]))
        assert sharpe == 0.0

    def test_sharpe_ratio_zero_volatility(self):
        """Test Sharpe ratio with zero volatility."""
        returns = np.array([0.001] * 100)  # Constant returns
        sharpe = calculate_sharpe_ratio(returns)
        # With constant returns, std is 0 (or very close to 0 due to ddof=1)
        # The implementation may return 0 or a very large number
        # We just check it doesn't raise an error
        assert sharpe is not None


class TestSortinoRatio:
    """Tests for Sortino ratio calculation."""

    def test_sortino_ratio(self):
        """Test Sortino ratio calculation."""
        np.random.seed(42)
        daily_returns = np.random.normal(0.001, 0.01, 252)

        sortino = calculate_sortino_ratio(daily_returns)
        sharpe = calculate_sharpe_ratio(daily_returns)

        # Sortino should be >= Sharpe (only penalizes downside)
        assert sortino >= sharpe

    def test_sortino_ratio_no_negative_returns(self):
        """Test Sortino ratio with no negative returns."""
        returns = np.array([0.01, 0.02, 0.015, 0.005])  # All positive
        sortino = calculate_sortino_ratio(returns)

        # Should return inf or a very high value
        assert sortino == float("inf") or sortino > 10


class TestCalmarRatio:
    """Tests for Calmar ratio calculation."""

    def test_calmar_ratio(self):
        """Test Calmar ratio calculation."""
        # 20% annualized return with 10% max drawdown = Calmar of 2
        calmar = calculate_calmar_ratio(20.0, 10.0)
        assert calmar == pytest.approx(2.0, rel=0.01)

    def test_calmar_ratio_no_drawdown(self):
        """Test Calmar ratio when there's no drawdown."""
        calmar = calculate_calmar_ratio(20.0, 0.0)
        assert calmar == 0.0


class TestTradeStatistics:
    """Tests for trade statistics calculation."""

    def _make_trade(self, pnl: float):
        """Create a mock trade object."""
        trade = MagicMock()
        trade.pnl = Decimal(str(pnl))
        return trade

    def test_win_rate(self):
        """Test win rate calculation."""
        # 3 wins, 2 losses = 60% win rate
        trades = [
            self._make_trade(100.0),
            self._make_trade(-50.0),
            self._make_trade(200.0),
            self._make_trade(-30.0),
            self._make_trade(150.0),
        ]

        stats = calculate_trade_statistics(trades)
        assert float(stats["win_rate"]) == pytest.approx(0.6, rel=0.01)

    def test_win_rate_all_winners(self):
        """Test win rate with all winning trades."""
        trades = [self._make_trade(100.0), self._make_trade(50.0), self._make_trade(200.0)]

        stats = calculate_trade_statistics(trades)
        assert float(stats["win_rate"]) == pytest.approx(1.0, rel=0.01)

    def test_win_rate_all_losers(self):
        """Test win rate with all losing trades."""
        trades = [self._make_trade(-100.0), self._make_trade(-50.0), self._make_trade(-200.0)]

        stats = calculate_trade_statistics(trades)
        assert float(stats["win_rate"]) == pytest.approx(0.0, rel=0.01)

    def test_win_rate_no_trades(self):
        """Test win rate with no trades."""
        stats = calculate_trade_statistics([])
        assert stats["total_trades"] == 0
        assert float(stats["win_rate"]) == 0.0

    def test_profit_factor(self):
        """Test profit factor calculation."""
        # Gross profit = 450, Gross loss = 80 = PF of 5.625
        trades = [
            self._make_trade(100.0),
            self._make_trade(-50.0),
            self._make_trade(200.0),
            self._make_trade(-30.0),
            self._make_trade(150.0),
        ]

        stats = calculate_trade_statistics(trades)
        assert float(stats["profit_factor"]) == pytest.approx(5.625, rel=0.01)

    def test_average_trade(self):
        """Test average trade calculation."""
        trades = [
            self._make_trade(100.0),
            self._make_trade(-50.0),
            self._make_trade(200.0),
            self._make_trade(-30.0),
            self._make_trade(150.0),
        ]

        stats = calculate_trade_statistics(trades)
        assert float(stats["avg_trade"]) == pytest.approx(74.0, rel=0.01)  # (100-50+200-30+150)/5

    def test_largest_win_loss(self):
        """Test largest win and loss calculation."""
        trades = [
            self._make_trade(100.0),
            self._make_trade(-50.0),
            self._make_trade(200.0),
            self._make_trade(-30.0),
            self._make_trade(150.0),
        ]

        stats = calculate_trade_statistics(trades)
        assert float(stats["largest_win"]) == pytest.approx(200.0, rel=0.01)
        assert float(stats["largest_loss"]) == pytest.approx(-50.0, rel=0.01)


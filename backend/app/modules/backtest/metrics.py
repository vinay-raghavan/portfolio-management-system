"""Performance metrics calculation for backtesting.

This module provides functions to calculate various performance metrics
including Sharpe ratio, Sortino ratio, max drawdown, and trade statistics.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any

import numpy as np


def calculate_metrics(
    trades: list,
    equity_curve: list[dict[str, Any]],
    initial_capital: Decimal,
    final_capital: Decimal,
    start_date: datetime,
    end_date: datetime,
    risk_free_rate: float = 0.05,  # 5% annual risk-free rate
) -> dict[str, Any]:
    """Calculate all performance metrics for a backtest.

    Args:
        trades: List of Trade objects
        equity_curve: List of equity points with date and equity
        initial_capital: Starting capital
        final_capital: Ending capital
        start_date: Backtest start date
        end_date: Backtest end date
        risk_free_rate: Annual risk-free rate for Sharpe calculation

    Returns:
        Dictionary with all calculated metrics
    """
    # Calculate returns
    total_return = calculate_total_return(initial_capital, final_capital)
    annualized_return = calculate_annualized_return(total_return, start_date, end_date)

    # Calculate risk metrics from equity curve
    returns = calculate_daily_returns(equity_curve)
    sharpe = calculate_sharpe_ratio(returns, risk_free_rate)
    sortino = calculate_sortino_ratio(returns, risk_free_rate)
    max_dd, drawdown_curve = calculate_max_drawdown(equity_curve)
    calmar = calculate_calmar_ratio(annualized_return, max_dd)

    # Calculate trade statistics
    trade_stats = calculate_trade_statistics(trades)

    return {
        "total_return": Decimal(str(round(total_return, 4))),
        "annualized_return": Decimal(str(round(annualized_return, 4))),
        "sharpe_ratio": Decimal(str(round(sharpe, 4))),
        "sortino_ratio": Decimal(str(round(sortino, 4))),
        "max_drawdown": Decimal(str(round(max_dd, 4))),
        "calmar_ratio": Decimal(str(round(calmar, 4))),
        "drawdown_curve": drawdown_curve,
        **trade_stats,
    }


def calculate_total_return(initial: Decimal, final: Decimal) -> float:
    """Calculate total return as percentage."""
    if initial == 0:
        return 0.0
    return float((final - initial) / initial * 100)


def calculate_annualized_return(
    total_return: float, start_date: datetime, end_date: datetime
) -> float:
    """Calculate annualized return from total return."""
    days = (end_date - start_date).days
    if days <= 0:
        return 0.0

    years = days / 365.25
    if years == 0:
        return 0.0

    # Convert percentage to decimal, annualize, convert back
    total_decimal = total_return / 100
    annualized = ((1 + total_decimal) ** (1 / years) - 1) * 100
    return annualized


def calculate_daily_returns(equity_curve: list[dict[str, Any]]) -> np.ndarray:
    """Calculate daily returns from equity curve."""
    if len(equity_curve) < 2:
        return np.array([])

    equities = [point["equity"] for point in equity_curve]
    returns = np.diff(equities) / equities[:-1]
    return returns


def calculate_sharpe_ratio(returns: np.ndarray, risk_free_rate: float = 0.05) -> float:
    """Calculate Sharpe ratio.

    Sharpe = (Mean Return - Risk Free Rate) / Std Dev of Returns
    """
    if len(returns) == 0:
        return 0.0

    # Convert annual risk-free rate to daily
    daily_rf = risk_free_rate / 252

    mean_return = np.mean(returns)
    std_return = np.std(returns, ddof=1)

    if std_return == 0:
        return 0.0

    # Annualize the Sharpe ratio
    sharpe = (mean_return - daily_rf) / std_return * np.sqrt(252)
    return float(sharpe)


def calculate_sortino_ratio(returns: np.ndarray, risk_free_rate: float = 0.05) -> float:
    """Calculate Sortino ratio.

    Sortino = (Mean Return - Risk Free Rate) / Downside Deviation
    Only considers negative returns for volatility.
    """
    if len(returns) == 0:
        return 0.0

    daily_rf = risk_free_rate / 252
    mean_return = np.mean(returns)

    # Calculate downside deviation (only negative returns)
    negative_returns = returns[returns < 0]
    if len(negative_returns) == 0:
        return float("inf") if mean_return > daily_rf else 0.0

    downside_std = np.std(negative_returns, ddof=1)
    if downside_std == 0:
        return 0.0

    sortino = (mean_return - daily_rf) / downside_std * np.sqrt(252)
    return float(sortino)


def calculate_max_drawdown(
    equity_curve: list[dict[str, Any]],
) -> tuple[float, list[dict[str, Any]]]:
    """Calculate maximum drawdown and drawdown curve.

    Returns:
        Tuple of (max_drawdown_percentage, drawdown_curve)
    """
    if len(equity_curve) == 0:
        return 0.0, []

    equities = [point["equity"] for point in equity_curve]
    dates = [point["date"] for point in equity_curve]

    peak = equities[0]
    max_dd = 0.0
    drawdown_curve = []

    for i, equity in enumerate(equities):
        if equity > peak:
            peak = equity

        drawdown = ((peak - equity) / peak) * 100 if peak > 0 else 0
        max_dd = max(max_dd, drawdown)

        drawdown_curve.append(
            {
                "date": dates[i],
                "drawdown": round(drawdown, 4),
            }
        )

    return max_dd, drawdown_curve


def calculate_calmar_ratio(annualized_return: float, max_drawdown: float) -> float:
    """Calculate Calmar ratio.

    Calmar = Annualized Return / Max Drawdown
    """
    if max_drawdown == 0:
        return 0.0
    return annualized_return / max_drawdown


def calculate_trade_statistics(trades: list) -> dict[str, Any]:
    """Calculate trade statistics from list of trades.

    Args:
        trades: List of Trade objects with pnl attribute

    Returns:
        Dictionary with trade statistics
    """
    if not trades:
        return {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": Decimal("0"),
            "profit_factor": Decimal("0"),
            "avg_win": Decimal("0"),
            "avg_loss": Decimal("0"),
            "avg_trade": Decimal("0"),
            "largest_win": Decimal("0"),
            "largest_loss": Decimal("0"),
        }

    total_trades = len(trades)
    pnls = [float(t.pnl) for t in trades if t.pnl is not None]

    if not pnls:
        return {
            "total_trades": total_trades,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": Decimal("0"),
            "profit_factor": Decimal("0"),
            "avg_win": Decimal("0"),
            "avg_loss": Decimal("0"),
            "avg_trade": Decimal("0"),
            "largest_win": Decimal("0"),
            "largest_loss": Decimal("0"),
        }

    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]

    winning_trades = len(wins)
    losing_trades = len(losses)
    win_rate = winning_trades / total_trades if total_trades > 0 else 0

    # Profit factor = gross profit / gross loss
    gross_profit = sum(wins) if wins else 0
    gross_loss = abs(sum(losses)) if losses else 0
    profit_factor = (
        gross_profit / gross_loss if gross_loss > 0 else float("inf") if gross_profit > 0 else 0
    )

    # Average metrics
    avg_win = sum(wins) / len(wins) if wins else 0
    avg_loss = sum(losses) / len(losses) if losses else 0
    avg_trade = sum(pnls) / len(pnls) if pnls else 0

    # Extremes
    largest_win = max(wins) if wins else 0
    largest_loss = min(losses) if losses else 0

    return {
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate": Decimal(str(round(win_rate, 4))),
        "profit_factor": Decimal(str(round(profit_factor, 4)))
        if profit_factor != float("inf")
        else Decimal("999.9999"),
        "avg_win": Decimal(str(round(avg_win, 4))),
        "avg_loss": Decimal(str(round(avg_loss, 4))),
        "avg_trade": Decimal(str(round(avg_trade, 4))),
        "largest_win": Decimal(str(round(largest_win, 4))),
        "largest_loss": Decimal(str(round(largest_loss, 4))),
    }

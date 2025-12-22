"""Position sizing service for algo trading.

Calculates optimal position sizes based on various methods.
"""

import logging
from dataclasses import dataclass
from decimal import Decimal

from app.modules.algo.models import PositionSizingMethod
from app.providers.schemas import Funds

logger = logging.getLogger(__name__)


@dataclass
class PositionSizeResult:
    """Result of position sizing calculation."""

    quantity: int
    method_used: PositionSizingMethod
    target_value: Decimal
    risk_amount: Decimal | None = None
    notes: str | None = None


class PositionSizer:
    """Calculates position sizes for algo trading.

    Supports multiple sizing methods:
    - Fixed quantity
    - Fixed amount
    - Percentage of portfolio
    - Risk-based (Kelly criterion / fixed risk per trade)
    - Volatility-adjusted (ATR-based)
    """

    def calculate(
        self,
        method: PositionSizingMethod,
        price: Decimal,
        funds: Funds,
        fixed_quantity: int | None = None,
        fixed_amount: Decimal | None = None,
        portfolio_percent: Decimal = Decimal("5.0"),
        risk_per_trade_percent: Decimal = Decimal("2.0"),
        stop_loss: Decimal | None = None,
        atr: Decimal | None = None,
        max_position_value: Decimal | None = None,
    ) -> PositionSizeResult:
        """Calculate position size based on specified method.

        Args:
            method: Position sizing method to use
            price: Current/entry price
            funds: Account funds information
            fixed_quantity: Fixed quantity for FIXED_QUANTITY method
            fixed_amount: Fixed amount for FIXED_AMOUNT method
            portfolio_percent: Portfolio percentage for PERCENT_OF_PORTFOLIO
            risk_per_trade_percent: Risk per trade for RISK_BASED method
            stop_loss: Stop loss price for risk calculations
            atr: Average True Range for volatility adjustment
            max_position_value: Maximum position value cap

        Returns:
            PositionSizeResult with calculated quantity
        """
        if price <= 0:
            return PositionSizeResult(
                quantity=0,
                method_used=method,
                target_value=Decimal("0"),
                notes="Invalid price",
            )

        result: PositionSizeResult

        if method == PositionSizingMethod.FIXED_QUANTITY:
            result = self._fixed_quantity(fixed_quantity or 1, price)

        elif method == PositionSizingMethod.FIXED_AMOUNT:
            result = self._fixed_amount(fixed_amount or Decimal("10000"), price)

        elif method == PositionSizingMethod.PERCENT_OF_PORTFOLIO:
            result = self._percent_of_portfolio(funds, price, portfolio_percent)

        elif method == PositionSizingMethod.RISK_BASED:
            result = self._risk_based(funds, price, stop_loss, risk_per_trade_percent)

        elif method == PositionSizingMethod.VOLATILITY_ADJUSTED:
            result = self._volatility_adjusted(funds, price, atr, risk_per_trade_percent)

        else:
            # Default fallback
            result = self._fixed_quantity(1, price)

        # Apply maximum position value cap
        if max_position_value and result.target_value > max_position_value:
            capped_quantity = int(max_position_value / price)
            result = PositionSizeResult(
                quantity=max(1, capped_quantity),
                method_used=method,
                target_value=Decimal(capped_quantity) * price,
                risk_amount=result.risk_amount,
                notes=f"Capped from {result.quantity} to {capped_quantity} by max position value",
            )

        return result

    def _fixed_quantity(self, quantity: int, price: Decimal) -> PositionSizeResult:
        """Fixed number of shares."""
        return PositionSizeResult(
            quantity=max(1, quantity),
            method_used=PositionSizingMethod.FIXED_QUANTITY,
            target_value=Decimal(quantity) * price,
        )

    def _fixed_amount(self, amount: Decimal, price: Decimal) -> PositionSizeResult:
        """Fixed rupee amount."""
        quantity = int(amount / price)
        return PositionSizeResult(
            quantity=max(1, quantity),
            method_used=PositionSizingMethod.FIXED_AMOUNT,
            target_value=amount,
        )

    def _percent_of_portfolio(
        self,
        funds: Funds,
        price: Decimal,
        percent: Decimal,
    ) -> PositionSizeResult:
        """Percentage of total portfolio value."""
        target_value = funds.total_balance * (percent / Decimal("100"))
        quantity = int(target_value / price)
        return PositionSizeResult(
            quantity=max(1, quantity),
            method_used=PositionSizingMethod.PERCENT_OF_PORTFOLIO,
            target_value=target_value,
            notes=f"{percent}% of ₹{funds.total_balance:.2f}",
        )

    def _risk_based(
        self,
        funds: Funds,
        price: Decimal,
        stop_loss: Decimal | None,
        risk_percent: Decimal,
    ) -> PositionSizeResult:
        """Risk-based sizing: risk a fixed % of portfolio per trade."""
        risk_amount = funds.total_balance * (risk_percent / Decimal("100"))

        if not stop_loss:
            # Fallback: use 2% of price as assumed risk
            assumed_risk = price * Decimal("0.02")
            quantity = int(risk_amount / assumed_risk)
            return PositionSizeResult(
                quantity=max(1, quantity),
                method_used=PositionSizingMethod.RISK_BASED,
                target_value=Decimal(quantity) * price,
                risk_amount=risk_amount,
                notes="No stop loss, using 2% price as risk",
            )

        risk_per_share = abs(price - stop_loss)
        if risk_per_share <= 0:
            return PositionSizeResult(
                quantity=1,
                method_used=PositionSizingMethod.RISK_BASED,
                target_value=price,
                risk_amount=risk_amount,
                notes="Stop loss too close to price",
            )

        quantity = int(risk_amount / risk_per_share)
        return PositionSizeResult(
            quantity=max(1, quantity),
            method_used=PositionSizingMethod.RISK_BASED,
            target_value=Decimal(quantity) * price,
            risk_amount=risk_amount,
            notes=f"Risking ₹{risk_amount:.2f} with ₹{risk_per_share:.2f}/share risk",
        )

    def _volatility_adjusted(
        self,
        funds: Funds,
        price: Decimal,
        atr: Decimal | None,
        risk_percent: Decimal,
    ) -> PositionSizeResult:
        """Volatility-adjusted sizing using ATR.

        Uses ATR as a proxy for volatility. Lower volatility = larger position.
        Position size = Risk Amount / (ATR * multiplier)
        """
        risk_amount = funds.total_balance * (risk_percent / Decimal("100"))

        if not atr or atr <= 0:
            # Fallback: use 3% of price as assumed ATR
            atr = price * Decimal("0.03")
            notes_suffix = " (estimated ATR)"
        else:
            notes_suffix = ""

        # Use 2x ATR as the risk per share (typical for swing trading)
        atr_multiplier = Decimal("2")
        risk_per_share = atr * atr_multiplier

        quantity = int(risk_amount / risk_per_share)
        return PositionSizeResult(
            quantity=max(1, quantity),
            method_used=PositionSizingMethod.VOLATILITY_ADJUSTED,
            target_value=Decimal(quantity) * price,
            risk_amount=risk_amount,
            notes=f"ATR={atr:.2f}, risk/share=₹{risk_per_share:.2f}{notes_suffix}",
        )

    @staticmethod
    def calculate_atr(highs: list[Decimal], lows: list[Decimal], closes: list[Decimal], period: int = 14) -> Decimal:
        """Calculate Average True Range from price data.

        Args:
            highs: List of high prices
            lows: List of low prices
            closes: List of close prices
            period: ATR period (default 14)

        Returns:
            ATR value
        """
        if len(highs) < period + 1:
            return Decimal("0")

        true_ranges = []
        for i in range(1, len(highs)):
            high_low = highs[i] - lows[i]
            high_close = abs(highs[i] - closes[i - 1])
            low_close = abs(lows[i] - closes[i - 1])
            true_range = max(high_low, high_close, low_close)
            true_ranges.append(true_range)

        # Simple moving average of True Range
        recent_trs = true_ranges[-period:]
        atr = sum(recent_trs) / Decimal(len(recent_trs))
        return atr


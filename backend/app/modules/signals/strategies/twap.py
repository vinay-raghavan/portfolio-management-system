"""TWAP (Time Weighted Average Price) Strategy.

Executes orders by splitting them into equal time slices.
Used to minimize market impact when executing large orders.
"""

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from decimal import Decimal

import pandas as pd

from app.modules.signals.models import SignalType
from app.modules.signals.strategies.base import BaseStrategy, SignalData
from app.modules.signals.strategies.registry import StrategyRegistry


@dataclass
class TWAPSlice:
    """A single TWAP execution slice."""

    slice_number: int
    total_slices: int
    quantity: int
    scheduled_time: datetime
    executed: bool = False
    executed_price: Decimal | None = None
    executed_time: datetime | None = None


@dataclass
class TWAPPlan:
    """Complete TWAP execution plan."""

    symbol: str
    total_quantity: int
    direction: SignalType  # BUY or SELL
    start_time: datetime
    end_time: datetime
    slices: list[TWAPSlice]
    avg_executed_price: Decimal | None = None
    total_executed: int = 0


@StrategyRegistry.register
class TWAPStrategy(BaseStrategy):
    """Time Weighted Average Price (TWAP) Strategy.

    TWAP is an execution algorithm that:
    1. Splits a large order into smaller equal-sized slices
    2. Executes each slice at regular time intervals
    3. Aims to achieve average price close to TWAP

    This strategy generates signals for each time slice,
    allowing the algo engine to execute incrementally.

    Use cases:
    - Large institutional orders
    - Reducing market impact
    - Benchmark execution (vs TWAP)
    - Passive accumulation/distribution

    Note: This is an EXECUTION strategy, not a signal strategy.
    It assumes you already have a directional view.
    """

    name = "twap"
    description = "TWAP - Split orders across time intervals"
    default_timeframe = "5m"

    # NSE market hours
    MARKET_OPEN = time(9, 15)
    MARKET_CLOSE = time(15, 30)

    def __init__(
        self,
        num_slices: int = 10,  # Number of time slices
        duration_minutes: int = 60,  # Total execution duration
        randomize_pct: float = 10.0,  # Random variance in slice timing
        min_slice_quantity: int = 1,  # Minimum quantity per slice
        participation_rate: float = 0.1,  # Max % of volume to participate
        price_limit_pct: float | None = None,  # Optional limit price as % from start
        aggressive_finish: bool = False,  # Complete remaining at end
    ):
        """Initialize TWAP strategy.

        Args:
            num_slices: Number of equal time slices
            duration_minutes: Total duration to execute over
            randomize_pct: Random variance in timing (0-100%)
            min_slice_quantity: Minimum quantity per slice
            participation_rate: Max % of average volume per slice
            price_limit_pct: Optional price limit as % from start price
            aggressive_finish: Execute remaining quantity at end
        """
        self.num_slices = num_slices
        self.duration_minutes = duration_minutes
        self.randomize_pct = randomize_pct
        self.min_slice_quantity = min_slice_quantity
        self.participation_rate = participation_rate
        self.price_limit_pct = Decimal(str(price_limit_pct)) if price_limit_pct else None
        self.aggressive_finish = aggressive_finish

        # Track active TWAP plans
        self._active_plans: dict[str, TWAPPlan] = {}

    def get_parameters(self) -> dict:
        """Return the strategy's configurable parameters."""
        return {
            "num_slices": self.num_slices,
            "duration_minutes": self.duration_minutes,
            "randomize_pct": self.randomize_pct,
            "min_slice_quantity": self.min_slice_quantity,
            "participation_rate": self.participation_rate,
            "price_limit_pct": float(self.price_limit_pct) if self.price_limit_pct else None,
            "aggressive_finish": self.aggressive_finish,
        }

    def _to_decimal(self, value: float) -> Decimal:
        """Convert float to Decimal."""
        return Decimal(str(round(value, 2)))

    def create_twap_plan(
        self,
        symbol: str,
        total_quantity: int,
        direction: SignalType,
        start_time: datetime | None = None,
    ) -> TWAPPlan:
        """Create a TWAP execution plan.

        Args:
            symbol: Stock symbol
            total_quantity: Total quantity to execute
            direction: BUY or SELL
            start_time: When to start (default: now)

        Returns:
            TWAPPlan with all slices scheduled
        """
        if start_time is None:
            start_time = datetime.now()

        # Calculate slice interval
        interval_seconds = (self.duration_minutes * 60) / self.num_slices

        # Calculate quantity per slice
        base_quantity = total_quantity // self.num_slices
        remainder = total_quantity % self.num_slices

        slices = []
        current_time = start_time

        for i in range(self.num_slices):
            # Add remainder to last slices
            slice_qty = base_quantity
            if i >= self.num_slices - remainder:
                slice_qty += 1

            # Ensure minimum quantity
            if slice_qty < self.min_slice_quantity and i < self.num_slices - 1:
                continue  # Skip this slice, will be added to later ones

            slices.append(
                TWAPSlice(
                    slice_number=len(slices) + 1,
                    total_slices=self.num_slices,
                    quantity=slice_qty,
                    scheduled_time=current_time,
                )
            )

            current_time += timedelta(seconds=interval_seconds)

        end_time = start_time + timedelta(minutes=self.duration_minutes)

        plan = TWAPPlan(
            symbol=symbol,
            total_quantity=total_quantity,
            direction=direction,
            start_time=start_time,
            end_time=end_time,
            slices=slices,
        )

        self._active_plans[symbol] = plan
        return plan

    def get_current_slice(self, symbol: str) -> TWAPSlice | None:
        """Get the current slice to execute for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Current TWAPSlice or None if no active plan/slice
        """
        plan = self._active_plans.get(symbol)
        if not plan:
            return None

        now = datetime.now()

        for slice_info in plan.slices:
            if not slice_info.executed and slice_info.scheduled_time <= now:
                return slice_info

        return None

    def mark_slice_executed(
        self,
        symbol: str,
        slice_number: int,
        executed_price: Decimal,
    ) -> None:
        """Mark a slice as executed.

        Args:
            symbol: Stock symbol
            slice_number: Slice number that was executed
            executed_price: Price at which it was executed
        """
        plan = self._active_plans.get(symbol)
        if not plan:
            return

        for slice_info in plan.slices:
            if slice_info.slice_number == slice_number:
                slice_info.executed = True
                slice_info.executed_price = executed_price
                slice_info.executed_time = datetime.now()
                plan.total_executed += slice_info.quantity

                # Update average price
                if plan.avg_executed_price is None:
                    plan.avg_executed_price = executed_price
                else:
                    # Weighted average
                    prev_value = plan.avg_executed_price * (
                        plan.total_executed - slice_info.quantity
                    )
                    new_value = executed_price * slice_info.quantity
                    plan.avg_executed_price = (prev_value + new_value) / plan.total_executed
                break

    def generate_signals(self, df: pd.DataFrame, symbol: str) -> list[SignalData]:
        """Generate TWAP execution signals.

        This checks if there's an active TWAP plan and if the current
        time matches a slice execution time.

        Args:
            df: OHLCV DataFrame
            symbol: Stock symbol

        Returns:
            List with one SignalData if a slice should execute
        """
        if df.empty:
            return []

        # Check for active plan
        plan = self._active_plans.get(symbol)
        if not plan:
            return []

        # Get current slice to execute
        current_slice = self.get_current_slice(symbol)
        if not current_slice:
            return []

        current_price = self._to_decimal(df["Close"].iloc[-1])

        # Check price limit if configured
        if self.price_limit_pct:
            first_slice = plan.slices[0]
            if first_slice.executed and first_slice.executed_price:
                start_price = first_slice.executed_price
                limit_pct = self.price_limit_pct / 100

                if plan.direction == SignalType.BUY:
                    max_price = start_price * (1 + limit_pct)
                    if current_price > max_price:
                        return []  # Price moved too high
                else:
                    min_price = start_price * (1 - limit_pct)
                    if current_price < min_price:
                        return []  # Price moved too low

        # Calculate progress
        progress = current_slice.slice_number / current_slice.total_slices
        remaining_qty = plan.total_quantity - plan.total_executed

        signal = SignalData(
            symbol=symbol,
            signal_type=plan.direction,
            strength=Decimal("0.7"),  # Fixed strength for execution
            confidence=Decimal("0.9"),  # High confidence (it's execution)
            price_at_signal=current_price,
            entry_price=current_price,
            stop_loss=None,  # TWAP doesn't use stop loss
            take_profit=None,
            risk_reward_ratio=Decimal("0"),
            indicators={
                "twap_slice": current_slice.slice_number,
                "twap_total_slices": current_slice.total_slices,
                "twap_slice_quantity": current_slice.quantity,
                "twap_progress_pct": round(progress * 100, 1),
                "twap_remaining_qty": remaining_qty,
                "twap_avg_price": float(plan.avg_executed_price)
                if plan.avg_executed_price
                else None,
            },
            notes=f"TWAP slice {current_slice.slice_number}/{current_slice.total_slices}, qty={current_slice.quantity}",
        )

        return [signal]

    def get_plan_status(self, symbol: str) -> dict | None:
        """Get status of TWAP plan for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Status dict or None if no plan
        """
        plan = self._active_plans.get(symbol)
        if not plan:
            return None

        executed_slices = sum(1 for s in plan.slices if s.executed)

        return {
            "symbol": plan.symbol,
            "direction": plan.direction.value,
            "total_quantity": plan.total_quantity,
            "total_executed": plan.total_executed,
            "remaining_quantity": plan.total_quantity - plan.total_executed,
            "slices_executed": executed_slices,
            "total_slices": len(plan.slices),
            "avg_executed_price": float(plan.avg_executed_price)
            if plan.avg_executed_price
            else None,
            "start_time": plan.start_time.isoformat(),
            "end_time": plan.end_time.isoformat(),
            "is_complete": plan.total_executed >= plan.total_quantity,
        }

    def cancel_plan(self, symbol: str) -> bool:
        """Cancel an active TWAP plan.

        Args:
            symbol: Stock symbol

        Returns:
            True if plan was cancelled
        """
        if symbol in self._active_plans:
            del self._active_plans[symbol]
            return True
        return False

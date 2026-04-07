"""Pydantic schemas for algo trading module."""

from datetime import datetime, time
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field

from app.modules.algo.models import (
    ExecutionStatus,
    PortfolioSafetyActionMode,
    PortfolioSafetyThresholdType,
    PositionSizingMethod,
    ProfitCutoffAction,
    ScheduleType,
    SignalDirection,
    StrategyProductType,
    StrategyStatus,
)
from app.modules.portfolio.schemas import ProfitBookingRule, ProfitBookingRules

# ============== Universe Schemas ==============


class UniverseBase(BaseModel):
    """Base universe schema."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    symbols: list[str] | None = None
    filter_criteria: dict | None = None
    is_dynamic: bool = False


class UniverseCreate(UniverseBase):
    """Create universe request."""

    pass


class UniverseUpdate(BaseModel):
    """Update universe request."""

    name: str | None = None
    description: str | None = None
    symbols: list[str] | None = None
    filter_criteria: dict | None = None


class UniverseResponse(UniverseBase):
    """Universe response."""

    id: str
    user_id: str | None
    is_system: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============== User Strategy Schemas ==============


class PositionSizingConfig(BaseModel):
    """Position sizing configuration."""

    method: PositionSizingMethod = PositionSizingMethod.PERCENT_OF_PORTFOLIO
    fixed_quantity: int | None = None
    fixed_amount: Decimal | None = None
    portfolio_percent: Decimal = Decimal("5.00")
    risk_per_trade_percent: Decimal = Decimal("2.00")
    max_position_value: Decimal | None = None


class ScheduleConfig(BaseModel):
    """Schedule configuration for strategy execution."""

    schedule_type: ScheduleType = ScheduleType.MARKET_OPEN
    interval_seconds: int | None = None
    cron_expression: str | None = None
    timeframe: str = "1d"
    # Trading time window fields
    trading_start_time: time | None = Field(
        default=None, description="Start time for trading window (e.g., 09:45)"
    )
    trading_end_time: time | None = Field(
        default=None, description="End time for trading window (e.g., 15:15)"
    )
    trading_timezone: str = Field(
        default="Asia/Kolkata", description="IANA timezone for time window"
    )
    active_trading_days: list[int] | None = Field(
        default=None,
        description="Weekday indices (0=Monday, 6=Sunday). Default: [0,1,2,3,4] (Mon-Fri)",
    )


class RiskConfig(BaseModel):
    """Risk control configuration."""

    max_daily_trades: int = Field(default=10, ge=1, le=100)
    max_daily_loss: Decimal = Field(default=Decimal("5000.00"), ge=0)
    max_open_positions: int = Field(default=5, ge=1, le=50)
    cooldown_seconds: int = Field(default=60, ge=0)
    max_consecutive_losses: int = Field(default=3, ge=1, le=20)
    max_drawdown_percent: Decimal = Field(default=Decimal("10.00"), ge=0, le=100)
    # Max unrealized loss - triggers circuit breaker when open positions are down this much
    max_unrealized_loss: Decimal | None = Field(default=None, ge=0)
    # Profit cutoff settings
    max_daily_profit: Decimal | None = Field(default=None, ge=0)
    overall_profit_target: Decimal | None = Field(default=None, ge=0)
    profit_cutoff_action: ProfitCutoffAction = Field(default=ProfitCutoffAction.PAUSE_STRATEGY)


class UserStrategyBase(BaseModel):
    """Base user strategy schema."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    strategy_name: str = Field(..., min_length=1, max_length=50)
    is_paper_trading: bool = True


class UserStrategyCreate(UserStrategyBase):
    """Create user strategy request."""

    strategy_params: dict | None = None
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)
    position_sizing: PositionSizingConfig = Field(default_factory=PositionSizingConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    universe_id: str | None = None
    custom_symbols: list[str] | None = None


class UserStrategyUpdate(BaseModel):
    """Update user strategy request."""

    name: str | None = None
    description: str | None = None
    strategy_params: dict | None = None
    schedule: ScheduleConfig | None = None
    position_sizing: PositionSizingConfig | None = None
    risk: RiskConfig | None = None
    universe_id: str | None = None
    custom_symbols: list[str] | None = None
    is_paper_trading: bool | None = None


class UserStrategyResponse(UserStrategyBase):
    """User strategy response."""

    id: str
    user_id: str
    status: StrategyStatus
    strategy_params: dict | None
    schedule_type: ScheduleType
    interval_seconds: int | None
    cron_expression: str | None
    timeframe: str
    universe_id: str | None
    custom_symbols: list[str] | None
    position_sizing_method: PositionSizingMethod
    fixed_quantity: int | None
    fixed_amount: Decimal | None
    portfolio_percent: Decimal
    risk_per_trade_percent: Decimal
    max_position_value: Decimal | None
    max_daily_trades: int
    max_daily_loss: Decimal
    max_open_positions: int
    cooldown_seconds: int
    max_consecutive_losses: int
    max_drawdown_percent: Decimal
    max_unrealized_loss: Decimal | None
    max_daily_profit: Decimal | None
    overall_profit_target: Decimal | None
    profit_cutoff_action: ProfitCutoffAction
    last_run_at: datetime | None
    next_run_at: datetime | None
    total_trades: int
    winning_trades: int
    total_pnl: Decimal
    consecutive_losses: int
    created_at: datetime
    updated_at: datetime

    # Screener linking fields
    linked_screener_id: str | None = None
    sync_from_screener: bool = True
    linked_screener_name: str | None = None  # For UI display

    class Config:
        from_attributes = True


class UserStrategySummary(BaseModel):
    """Minimal strategy info for listing."""

    id: str
    name: str
    strategy_name: str
    status: StrategyStatus
    is_paper_trading: bool
    total_trades: int
    winning_trades: int
    total_pnl: Decimal
    last_run_at: datetime | None
    next_run_at: datetime | None

    class Config:
        from_attributes = True


# ============== Execution Schemas ==============


class ExecutionResponse(BaseModel):
    """Strategy execution log response."""

    id: str
    strategy_id: str
    status: ExecutionStatus
    started_at: datetime
    completed_at: datetime | None
    duration_ms: int | None
    symbols_analyzed: int
    signals_generated: int
    orders_placed: int
    orders_filled: int
    orders_rejected: int
    signals_data: list | None
    orders_data: list | None
    error_message: str | None

    class Config:
        from_attributes = True


class AlgoOrderResponse(BaseModel):
    """Algo order response."""

    id: str
    execution_id: str
    order_id: str
    signal_id: str | None
    strategy_id: str
    symbol: str
    side: str
    quantity: int
    order_type: str
    price: Decimal | None
    signal_type: str | None
    signal_strength: Decimal | None
    sizing_method: str | None
    risk_amount: Decimal | None
    created_at: datetime

    class Config:
        from_attributes = True


# ============== Kill Switch Schemas ==============


class KillSwitchStatus(BaseModel):
    """Kill switch status response."""

    is_active: bool
    activated_at: datetime | None = None
    activated_by: str | None = None
    reason: str | None = None
    square_off_initiated: bool = False


class KillSwitchActivate(BaseModel):
    """Kill switch activation request."""

    reason: str | None = None
    square_off_positions: bool = False


class CircuitBreakerStatus(BaseModel):
    """Circuit breaker status for a strategy."""

    strategy_id: str
    is_triggered: bool
    trigger_reason: str | None = None
    triggered_at: datetime | None = None
    daily_loss: Decimal
    max_daily_loss: Decimal
    consecutive_losses: int
    max_consecutive_losses: int
    current_drawdown_percent: Decimal
    max_drawdown_percent: Decimal
    # Unrealized loss tracking
    current_unrealized_loss: Decimal = Decimal("0")
    max_unrealized_loss: Decimal | None = None
    # Profit cutoff tracking
    daily_profit: Decimal = Decimal("0")
    max_daily_profit: Decimal | None = None
    overall_profit: Decimal = Decimal("0")
    overall_profit_target: Decimal | None = None
    profit_cutoff_triggered: bool = False


# ============== Algo Dashboard Schemas ==============


class AlgoDashboardStats(BaseModel):
    """Dashboard statistics."""

    total_strategies: int
    active_strategies: int
    paused_strategies: int
    total_executions_today: int
    total_orders_today: int
    total_pnl_today: Decimal
    kill_switch_active: bool


class ManualTriggerRequest(BaseModel):
    """Request to manually trigger a strategy."""

    symbols: list[str] | None = None  # Optional override


class ManualTriggerResponse(BaseModel):
    """Response from manual trigger."""

    execution_id: str
    status: str
    message: str


# ============== Router-specific Schemas ==============


class StrategyCreate(BaseModel):
    """Create strategy request for router."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    strategy_type: str = Field(..., min_length=1, max_length=50)
    strategy_config: dict | None = None
    universe_id: str | None = None
    symbols: list[str] | None = None
    schedule_type: ScheduleType = ScheduleType.MARKET_OPEN
    interval_seconds: int | None = None
    cron_expression: str | None = None
    position_sizing_method: PositionSizingMethod = PositionSizingMethod.PERCENT_OF_PORTFOLIO
    position_size_value: Decimal = Decimal("5.00")
    max_position_value: Decimal | None = None
    max_daily_trades: int = Field(default=10, ge=1, le=100)
    max_daily_loss: Decimal = Decimal("5000.00")
    max_open_positions: int = Field(default=5, ge=1, le=50)
    max_consecutive_losses: int = 3
    max_daily_profit: Decimal | None = None
    overall_profit_target: Decimal | None = None
    profit_cutoff_action: ProfitCutoffAction = ProfitCutoffAction.PAUSE_STRATEGY
    is_paper_trading: bool = True
    # Product type for orders (CNC/MIS/MTF)
    product_type: StrategyProductType = StrategyProductType.DELIVERY
    # Signal direction (LONG/SHORT/BOTH)
    signal_direction: SignalDirection = SignalDirection.LONG
    # Strategy-level default fixed stop loss / take profit (as percentage, e.g. 2.0 = 2%)
    default_stop_loss_pct: Decimal | None = Field(
        default=None, ge=0, le=50, description="Fixed stop loss percentage (e.g., 2.0 = 2%)"
    )
    default_take_profit_pct: Decimal | None = Field(
        default=None, ge=0, le=100, description="Fixed take profit percentage (e.g., 4.0 = 4%)"
    )
    # Strategy-level default trailing stop and profit booking settings
    default_trailing_stop_enabled: bool = False
    default_trailing_stop_pct: Decimal | None = None
    default_profit_booking_rules: ProfitBookingRules | None = None
    # Profit lock: locks stop loss at profit level once threshold is reached
    default_profit_lock_enabled: bool = False
    # Trading time window fields
    trading_start_time: time | None = Field(
        default=None, description="Start time for trading window (e.g., 09:45)"
    )
    trading_end_time: time | None = Field(
        default=None, description="End time for trading window (e.g., 15:15)"
    )
    trading_timezone: str = Field(
        default="Asia/Kolkata", description="IANA timezone for time window"
    )
    active_trading_days: list[int] | None = Field(
        default=None,
        description="Weekday indices (0=Monday, 6=Sunday). Default: [0,1,2,3,4] (Mon-Fri)",
    )


class StrategyUpdate(BaseModel):
    """Update strategy request for router."""

    name: str | None = None
    description: str | None = None
    strategy_config: dict | None = None
    universe_id: str | None = None
    symbols: list[str] | None = None
    schedule_type: ScheduleType | None = None
    interval_seconds: int | None = None
    cron_expression: str | None = None
    position_sizing_method: PositionSizingMethod | None = None
    position_size_value: Decimal | None = None
    max_position_value: Decimal | None = None
    max_daily_trades: int | None = Field(default=None, ge=1, le=100)
    max_daily_loss: Decimal | None = None
    max_open_positions: int | None = Field(default=None, ge=1, le=50)
    max_consecutive_losses: int | None = None
    max_daily_profit: Decimal | None = None
    overall_profit_target: Decimal | None = None
    profit_cutoff_action: ProfitCutoffAction | None = None
    is_paper_trading: bool | None = None
    # Product type for orders (CNC/MIS/MTF)
    product_type: StrategyProductType | None = None
    # Signal direction (LONG/SHORT/BOTH)
    signal_direction: SignalDirection | None = None
    # Strategy-level default fixed stop loss / take profit
    default_stop_loss_pct: Decimal | None = Field(
        default=None, ge=0, le=50, description="Fixed stop loss percentage (e.g., 2.0 = 2%)"
    )
    default_take_profit_pct: Decimal | None = Field(
        default=None, ge=0, le=100, description="Fixed take profit percentage (e.g., 4.0 = 4%)"
    )
    # Strategy-level default trailing stop and profit booking settings
    default_trailing_stop_enabled: bool | None = None
    default_trailing_stop_pct: Decimal | None = None
    default_profit_booking_rules: ProfitBookingRules | None = None
    # Profit lock: locks stop loss at profit level once threshold is reached
    default_profit_lock_enabled: bool | None = None
    # Trading time window fields
    trading_start_time: time | None = None
    trading_end_time: time | None = None
    trading_timezone: str | None = None
    active_trading_days: list[int] | None = None


class RecentExecutionSummary(BaseModel):
    """Summary of a recent strategy execution with order details."""

    id: str
    status: ExecutionStatus
    started_at: datetime
    completed_at: datetime | None
    duration_ms: int | None
    signals_generated: int
    orders_placed: int
    orders_filled: int
    error_message: str | None
    realized_pnl: Decimal = Decimal("0")
    total_order_value: Decimal = Decimal("0")
    # Order details - includes symbol, price, quantity, side, filled info
    orders: list["AlgoOrderDetailResponse"] = []

    model_config = {"from_attributes": True}


class StrategyResponse(BaseModel):
    """Strategy response for router with recent execution details."""

    id: str
    user_id: str
    name: str
    description: str | None
    strategy_type: str  # Maps from strategy_name
    strategy_config: dict | None  # Maps from strategy_params
    status: StrategyStatus
    universe_id: str | None
    symbols: list[str] | None  # Maps from custom_symbols
    schedule_type: ScheduleType
    interval_seconds: int | None
    cron_expression: str | None
    position_sizing_method: PositionSizingMethod
    position_size_value: Decimal  # Maps from portfolio_percent (default sizing)
    max_position_value: Decimal | None
    max_daily_trades: int
    max_daily_loss: Decimal
    max_open_positions: int
    max_consecutive_losses: int
    max_daily_profit: Decimal | None
    overall_profit_target: Decimal | None
    profit_cutoff_action: ProfitCutoffAction
    is_paper_trading: bool
    # Product type for orders (CNC/MIS/MTF)
    product_type: StrategyProductType
    # Signal direction (LONG/SHORT/BOTH)
    signal_direction: SignalDirection
    # Strategy-level default fixed stop loss / take profit
    default_stop_loss_pct: Decimal | None = None
    default_take_profit_pct: Decimal | None = None
    # Strategy-level default trailing stop and profit booking settings
    default_trailing_stop_enabled: bool = False
    default_trailing_stop_pct: Decimal | None = None
    default_profit_booking_rules: ProfitBookingRules | None = None
    # Profit lock: locks stop loss at profit level once threshold is reached
    default_profit_lock_enabled: bool = False
    # Trading time window fields
    trading_start_time: time | None = None
    trading_end_time: time | None = None
    trading_timezone: str = "Asia/Kolkata"
    active_trading_days: list[int] | None = None
    last_run_at: datetime | None
    next_run_at: datetime | None
    total_trades: int
    winning_trades: int
    total_pnl: Decimal
    created_at: datetime
    updated_at: datetime
    # Recent execution runs with order details
    recent_executions: list[RecentExecutionSummary] = []
    # Screener linking fields
    linked_screener_id: str | None = None
    sync_from_screener: bool = True
    linked_screener_name: str | None = None

    model_config = {"from_attributes": True}

    @staticmethod
    def _get_linked_screener_name(obj) -> str | None:
        """Safely get linked screener name without triggering lazy loads."""
        from sqlalchemy.orm import InstanceState

        try:
            state: InstanceState = obj._sa_instance_state
            # Check if linked_screener is already loaded (not pending lazy load)
            if "linked_screener" in state.dict:
                screener = state.dict["linked_screener"]
                return screener.name if screener else None
            # Not loaded — don't trigger lazy load, just return None
            return None
        except Exception:
            return None

    @staticmethod
    def _parse_profit_booking_rules(rules_data: dict | list | None) -> "ProfitBookingRules | None":
        """Parse profit booking rules from database format.

        Handles both old format (list) and new format (dict with enabled/rules).
        """
        if not rules_data:
            return None

        # If it's already a dict with 'enabled' and 'rules', validate it
        if isinstance(rules_data, dict) and "enabled" in rules_data:
            return ProfitBookingRules.model_validate(rules_data)

        # Old format: list of rules (convert to new format)
        if isinstance(rules_data, list):
            # Convert old format to new format
            converted_rules = []
            for rule in rules_data:
                if isinstance(rule, dict):
                    # Old format uses profit_percent/book_percent
                    # New format uses target_pct/quantity_pct
                    converted_rules.append(
                        ProfitBookingRule(
                            target_pct=rule.get("profit_percent", rule.get("target_pct", 0)),
                            quantity_pct=rule.get("book_percent", rule.get("quantity_pct", 0)),
                        )
                    )
            return ProfitBookingRules(enabled=True, rules=converted_rules, executed=[])

        return None

    @classmethod
    def from_model(cls, obj, executions: list | None = None) -> "StrategyResponse":
        """Create response from UserStrategy model with optional pre-loaded executions.

        Args:
            obj: UserStrategy ORM model
            executions: Optional list of pre-loaded StrategyExecution objects
        """
        from sqlalchemy import inspect as sa_inspect

        # Build recent executions with order details
        recent_executions = []
        execution_list = executions if executions is not None else []

        for exec_obj in execution_list[:5]:  # Limit to 5 most recent
            orders = []
            # Check if algo_orders was loaded
            try:
                exec_insp = sa_inspect(exec_obj)
                orders_loaded = "algo_orders" in exec_insp.dict
            except Exception:
                orders_loaded = False

            if orders_loaded and exec_obj.algo_orders:
                orders = [
                    AlgoOrderDetailResponse.model_validate(order) for order in exec_obj.algo_orders
                ]
            recent_executions.append(
                RecentExecutionSummary(
                    id=exec_obj.id,
                    status=exec_obj.status,
                    started_at=exec_obj.started_at,
                    completed_at=exec_obj.completed_at,
                    duration_ms=exec_obj.duration_ms,
                    signals_generated=exec_obj.signals_generated,
                    orders_placed=exec_obj.orders_placed,
                    orders_filled=exec_obj.orders_filled,
                    error_message=exec_obj.error_message,
                    realized_pnl=exec_obj.realized_pnl,
                    total_order_value=exec_obj.total_order_value,
                    orders=orders,
                )
            )

        data = {
            "id": obj.id,
            "user_id": obj.user_id,
            "name": obj.name,
            "description": obj.description,
            "strategy_type": obj.strategy_name,
            "strategy_config": obj.strategy_params,
            "status": obj.status,
            "universe_id": obj.universe_id,
            "symbols": obj.custom_symbols,
            "schedule_type": obj.schedule_type,
            "interval_seconds": obj.interval_seconds,
            "cron_expression": obj.cron_expression,
            "position_sizing_method": obj.position_sizing_method,
            "position_size_value": obj.portfolio_percent,
            "max_position_value": obj.max_position_value,
            "max_daily_trades": obj.max_daily_trades,
            "max_daily_loss": obj.max_daily_loss,
            "max_open_positions": obj.max_open_positions,
            "max_consecutive_losses": obj.max_consecutive_losses,
            "max_daily_profit": obj.max_daily_profit,
            "overall_profit_target": obj.overall_profit_target,
            "profit_cutoff_action": obj.profit_cutoff_action,
            "is_paper_trading": obj.is_paper_trading,
            "product_type": obj.product_type,
            "signal_direction": obj.signal_direction,
            "default_stop_loss_pct": obj.default_stop_loss_pct,
            "default_take_profit_pct": obj.default_take_profit_pct,
            "default_trailing_stop_enabled": obj.default_trailing_stop_enabled,
            "default_trailing_stop_pct": obj.default_trailing_stop_pct,
            "default_profit_booking_rules": (
                cls._parse_profit_booking_rules(obj.default_profit_booking_rules)
                if obj.default_profit_booking_rules
                else None
            ),
            "default_profit_lock_enabled": obj.default_profit_lock_enabled,
            # Trading time window fields
            "trading_start_time": obj.trading_start_time,
            "trading_end_time": obj.trading_end_time,
            "trading_timezone": obj.trading_timezone or "Asia/Kolkata",
            "active_trading_days": obj.active_trading_days,
            "last_run_at": obj.last_run_at,
            "next_run_at": obj.next_run_at,
            "total_trades": obj.total_trades,
            "winning_trades": obj.winning_trades,
            "total_pnl": obj.total_pnl,
            "created_at": obj.created_at,
            "updated_at": obj.updated_at,
            "recent_executions": recent_executions,
            # Screener linking fields
            "linked_screener_id": getattr(obj, "linked_screener_id", None),
            "sync_from_screener": getattr(obj, "sync_from_screener", True),
            "linked_screener_name": cls._get_linked_screener_name(obj),
        }
        return cls(**data)

    @classmethod
    def model_validate(cls, obj, **kwargs):
        """Custom validation - use from_model() instead for optimized loading."""
        if hasattr(obj, "strategy_name"):
            # For backwards compatibility, create with empty executions
            # Use from_model() with pre-loaded executions for better performance
            return cls.from_model(obj, executions=[])
        return super().model_validate(obj, **kwargs)


class AlgoOrderDetailResponse(BaseModel):
    """Response for algo order details with execution info."""

    id: str
    execution_id: str
    order_id: str | None
    strategy_id: str
    symbol: str
    side: str
    quantity: int
    order_type: str
    price: Decimal | None
    order_status: str = "PENDING"
    filled_quantity: int = 0
    filled_price: Decimal | None = None
    order_value: Decimal = Decimal("0")
    filled_at: datetime | None = None
    signal_type: str | None
    signal_strength: Decimal | None
    sizing_method: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class ExecutionHistoryResponse(BaseModel):
    """Execution history response with order details."""

    id: str
    strategy_id: str
    status: ExecutionStatus
    started_at: datetime
    completed_at: datetime | None
    duration_ms: int | None
    symbols_analyzed: int
    signals_generated: int
    orders_placed: int
    orders_filled: int
    orders_rejected: int
    error_message: str | None
    # P&L tracking
    realized_pnl: Decimal = Decimal("0")
    unrealized_pnl: Decimal = Decimal("0")
    total_order_value: Decimal = Decimal("0")
    positions_opened: int = 0
    positions_closed: int = 0
    # Order details - includes symbol, price, quantity, side, filled info
    orders: list[AlgoOrderDetailResponse] = []

    model_config = {"from_attributes": True}

    @classmethod
    def model_validate(cls, obj, **kwargs):
        """Custom validation to include algo_orders from the model."""
        if hasattr(obj, "algo_orders"):
            # It's a StrategyExecution model, map fields including orders
            orders = [
                AlgoOrderDetailResponse.model_validate(order) for order in (obj.algo_orders or [])
            ]
            data = {
                "id": obj.id,
                "strategy_id": obj.strategy_id,
                "status": obj.status,
                "started_at": obj.started_at,
                "completed_at": obj.completed_at,
                "duration_ms": obj.duration_ms,
                "symbols_analyzed": obj.symbols_analyzed,
                "signals_generated": obj.signals_generated,
                "orders_placed": obj.orders_placed,
                "orders_filled": obj.orders_filled,
                "orders_rejected": obj.orders_rejected,
                "error_message": obj.error_message,
                "realized_pnl": obj.realized_pnl,
                "unrealized_pnl": obj.unrealized_pnl,
                "total_order_value": obj.total_order_value,
                "positions_opened": obj.positions_opened,
                "positions_closed": obj.positions_closed,
                "orders": orders,
            }
            return cls(**data)
        return super().model_validate(obj, **kwargs)


class KillSwitchResponse(BaseModel):
    """Kill switch status response for router."""

    is_active: bool
    activated_at: datetime | None = None
    reason: str | None = None
    square_off_initiated: bool = False


class KillSwitchToggle(BaseModel):
    """Kill switch toggle request."""

    activate: bool
    reason: str | None = None
    square_off: bool = False


class EmergencyStopMode(str, Enum):
    """Emergency stop behavior mode."""

    PAUSE_ONLY = "PAUSE_ONLY"
    PAUSE_AND_SQUARE_OFF = "PAUSE_AND_SQUARE_OFF"


class EmergencyStopRequest(BaseModel):
    """Emergency stop request."""

    mode: EmergencyStopMode = EmergencyStopMode.PAUSE_ONLY
    reason: str | None = None


class EmergencySquareOffSummary(BaseModel):
    """Square-off result summary for emergency stop."""

    strategies_targeted: int = 0
    strategies_squared_off: int = 0
    positions_closed: int = 0
    total_realized_pnl: Decimal = Field(default=Decimal("0"))
    errors: list[str] = Field(default_factory=list)


class EmergencyStopResponse(BaseModel):
    """Emergency stop response."""

    status: str
    mode: EmergencyStopMode
    strategies_disabled: int
    kill_switch_active: bool
    square_off_initiated: bool
    square_off_summary: EmergencySquareOffSummary | None = None


class PortfolioSafetyConfigBase(BaseModel):
    """Portfolio-level safety configuration."""

    enabled: bool = False
    threshold_type: PortfolioSafetyThresholdType = PortfolioSafetyThresholdType.PERCENT
    threshold_value: Decimal = Field(default=Decimal("5.00"), gt=Decimal("0"))
    action_mode: PortfolioSafetyActionMode = PortfolioSafetyActionMode.PAUSE_ONLY


class PortfolioSafetyConfigUpdate(BaseModel):
    """Update request for portfolio-level safety configuration."""

    enabled: bool | None = None
    threshold_type: PortfolioSafetyThresholdType | None = None
    threshold_value: Decimal | None = Field(default=None, gt=Decimal("0"))
    action_mode: PortfolioSafetyActionMode | None = None


class PortfolioSafetyConfigResponse(PortfolioSafetyConfigBase):
    """Portfolio-level safety configuration response."""

    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# NOTE: CircuitBreakerStatus is defined earlier in this file (line 248)
# This duplicate was removed to fix F811 redefinition error


# ============== P&L Schemas ==============


class PositionResponse(BaseModel):
    """Response for an algo position."""

    id: str
    strategy_id: str
    user_id: str
    symbol: str
    side: str
    status: str
    entry_quantity: int
    entry_price: Decimal
    entry_at: datetime
    exit_quantity: int | None
    exit_price: Decimal | None
    exit_at: datetime | None
    remaining_quantity: int
    realized_pnl: Decimal
    realized_pnl_percent: Decimal
    # Unrealized P&L fields (for open positions)
    current_price: Decimal | None = None
    unrealized_pnl: Decimal | None = None
    unrealized_pnl_percent: Decimal | None = None
    is_winner: bool | None
    stop_loss: Decimal | None
    take_profit: Decimal | None
    # Trailing stop fields
    trailing_stop_enabled: bool | None = None
    trailing_stop_pct: Decimal | None = None
    trailing_stop_price: Decimal | None = None
    # Profit lock fields
    profit_lock_enabled: bool | None = None
    profit_lock_activated: bool | None = None
    profit_lock_price: Decimal | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PnLSummary(BaseModel):
    """Overall P&L summary for a user's algo trading."""

    total_realized_pnl: Decimal = Field(default=Decimal("0"))
    total_unrealized_pnl: Decimal = Field(default=Decimal("0"))
    total_pnl: Decimal = Field(default=Decimal("0"))
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: Decimal = Field(default=Decimal("0"))
    open_positions: int = 0
    closed_positions: int = 0
    best_trade_pnl: Decimal = Field(default=Decimal("0"))
    worst_trade_pnl: Decimal = Field(default=Decimal("0"))
    average_trade_pnl: Decimal = Field(default=Decimal("0"))


class StrategyPnL(BaseModel):
    """P&L summary for a single strategy."""

    strategy_id: str
    strategy_name: str
    total_pnl: Decimal = Field(default=Decimal("0"))
    realized_pnl: Decimal = Field(default=Decimal("0"))
    unrealized_pnl: Decimal = Field(default=Decimal("0"))
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: Decimal = Field(default=Decimal("0"))
    open_positions: int = 0
    closed_positions: int = 0
    status: str


class PnLByStrategyResponse(BaseModel):
    """P&L breakdown by strategy."""

    strategies: list[StrategyPnL]
    total_realized_pnl: Decimal = Field(default=Decimal("0"))
    total_unrealized_pnl: Decimal = Field(default=Decimal("0"))
    total_pnl: Decimal = Field(default=Decimal("0"))


class DailyPnL(BaseModel):
    """P&L for a single day."""

    date: str  # YYYY-MM-DD
    realized_pnl: Decimal = Field(default=Decimal("0"))
    unrealized_pnl: Decimal = Field(default=Decimal("0"))
    total_pnl: Decimal = Field(default=Decimal("0"))
    trades_opened: int = 0
    trades_closed: int = 0
    cumulative_pnl: Decimal = Field(default=Decimal("0"))


class PnLHistoryResponse(BaseModel):
    """P&L history over time."""

    daily_pnl: list[DailyPnL]
    period_start: str
    period_end: str
    total_realized_pnl: Decimal = Field(default=Decimal("0"))
    total_days: int = 0
    profitable_days: int = 0
    losing_days: int = 0


class UnrealizedPnLPosition(BaseModel):
    """Unrealized P&L for a single open position."""

    position_id: str
    strategy_id: str
    symbol: str
    side: str
    quantity: int
    entry_price: Decimal
    current_price: Decimal
    unrealized_pnl: Decimal
    unrealized_pnl_percent: Decimal
    entry_value: Decimal
    current_value: Decimal


class UnrealizedPnLResponse(BaseModel):
    """Total unrealized P&L with position details."""

    positions: list[UnrealizedPnLPosition]
    total_unrealized_pnl: Decimal = Field(default=Decimal("0"))
    total_entry_value: Decimal = Field(default=Decimal("0"))
    total_current_value: Decimal = Field(default=Decimal("0"))
    positions_count: int = 0


# ============== Exit Position Schemas ==============


class ClosePositionRequest(BaseModel):
    """Request to close a position."""

    exit_price: Decimal | None = Field(
        default=None,
        description="Exit price. If not provided, will fetch current market price.",
    )
    quantity: int | None = Field(
        default=None,
        description="Quantity to close. If not provided, closes entire position.",
    )


class ClosePositionResponse(BaseModel):
    """Response from closing a position."""

    position_id: str
    symbol: str
    side: str
    closed_quantity: int
    remaining_quantity: int
    entry_price: Decimal
    exit_price: Decimal
    realized_pnl: Decimal
    realized_pnl_percent: Decimal
    is_winner: bool
    status: str
    message: str


class SquareOffStrategyRequest(BaseModel):
    """Request to square off all positions for a strategy."""

    exit_prices: dict[str, Decimal] | None = Field(
        default=None,
        description="Optional dict of symbol -> exit price. Missing symbols will use market price.",
    )


class SquareOffStrategyResponse(BaseModel):
    """Response from squaring off a strategy."""

    strategy_id: str
    strategy_name: str
    positions_closed: int
    total_realized_pnl: Decimal
    closed_positions: list[ClosePositionResponse]
    message: str


# ============== Strategy Type Schemas ==============


class StrategyParameterSchema(BaseModel):
    """Schema for a single strategy parameter."""

    name: str = Field(..., description="Parameter name")
    type: str = Field(..., description="Parameter type: int, float, bool, select")
    default: int | float | bool | str | None = Field(None, description="Default value")
    min_value: float | None = Field(None, description="Minimum allowed value")
    max_value: float | None = Field(None, description="Maximum allowed value")
    options: list[str] | None = Field(None, description="Valid options for select type")
    description: str = Field("", description="Parameter description")


class StrategyTypeInfo(BaseModel):
    """Information about a strategy type."""

    name: str = Field(..., description="Strategy name/identifier")
    description: str = Field(..., description="Strategy description")
    default_timeframe: str = Field(..., description="Default timeframe")
    parameters: dict = Field(default_factory=dict, description="Current parameter values")


class StrategyTypeDetailResponse(BaseModel):
    """Detailed response for a specific strategy type."""

    name: str = Field(..., description="Strategy name/identifier")
    description: str = Field(..., description="Strategy description")
    default_timeframe: str = Field(..., description="Default timeframe")
    parameters: list[StrategyParameterSchema] = Field(
        default_factory=list, description="Parameter schemas"
    )


# ============== Composite Strategy Schemas ==============


class CompositeStrategyComponent(BaseModel):
    """A component strategy within a composite strategy."""

    strategy: str = Field(..., min_length=1, description="Strategy type name (e.g., 'rsi', 'macd')")
    params: dict | None = Field(default=None, description="Custom parameters for this strategy")
    weight: float = Field(default=1.0, ge=0.0, le=10.0, description="Weight for WEIGHTED logic")
    required: bool = Field(default=False, description="Must agree in AND/MAJORITY logic")


class CompositeStrategyCreate(BaseModel):
    """Request to create a composite strategy."""

    name: str = Field(..., min_length=1, max_length=100, description="User-friendly name")
    description: str | None = Field(default=None, description="Strategy description")
    components: list[CompositeStrategyComponent] = Field(
        ..., min_length=2, max_length=5, description="2-5 component strategies to combine"
    )
    combine_logic: str = Field(
        default="AND",
        pattern="^(AND|OR|MAJORITY|WEIGHTED)$",
        description="Logic for combining signals: AND, OR, MAJORITY, or WEIGHTED",
    )
    min_agreement_pct: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Minimum agreement for MAJORITY logic"
    )
    # Execution settings (same as regular strategy)
    universe_id: str | None = None
    symbols: list[str] | None = None
    schedule_type: ScheduleType = ScheduleType.MARKET_OPEN
    interval_seconds: int | None = None
    cron_expression: str | None = None
    position_sizing_method: PositionSizingMethod = PositionSizingMethod.PERCENT_OF_PORTFOLIO
    position_size_value: Decimal = Decimal("5.00")
    max_position_value: Decimal | None = None
    max_daily_trades: int = Field(default=10, ge=1, le=100)
    max_daily_loss: Decimal = Decimal("5000.00")
    max_open_positions: int = Field(default=5, ge=1, le=50)
    max_consecutive_losses: int = 3
    # Profit cutoff settings
    max_daily_profit: Decimal | None = None
    overall_profit_target: Decimal | None = None
    profit_cutoff_action: ProfitCutoffAction = ProfitCutoffAction.PAUSE_STRATEGY
    is_paper_trading: bool = True
    product_type: StrategyProductType = StrategyProductType.DELIVERY
    # Strategy-level default fixed stop loss / take profit
    default_stop_loss_pct: Decimal | None = None
    default_take_profit_pct: Decimal | None = None
    # Strategy-level default trailing stop and profit booking settings
    default_trailing_stop_enabled: bool = False
    default_trailing_stop_pct: Decimal | None = None
    default_profit_booking_rules: ProfitBookingRules | None = None
    # Profit lock: locks stop loss at profit level once threshold is reached
    default_profit_lock_enabled: bool = False


class CompositeStrategyResponse(BaseModel):
    """Response for a created composite strategy."""

    id: str
    name: str
    description: str | None
    strategy_type: str  # Will be "composite_<name>"
    components: list[CompositeStrategyComponent]
    combine_logic: str
    message: str


class DSLStrategyCreate(BaseModel):
    """Request to create a DSL-based custom strategy."""

    name: str = Field(..., min_length=1, max_length=100, description="User-friendly name")
    description: str | None = Field(default=None, description="Strategy description")
    definition: dict = Field(
        ..., description="DSL strategy definition with rules, indicators, etc."
    )
    # Execution settings (same as regular strategy)
    universe_id: str | None = None
    symbols: list[str] | None = None
    schedule_type: ScheduleType = ScheduleType.MARKET_OPEN
    interval_seconds: int | None = None
    cron_expression: str | None = None
    position_sizing_method: PositionSizingMethod = PositionSizingMethod.PERCENT_OF_PORTFOLIO
    position_size_value: Decimal = Decimal("5.00")
    max_position_value: Decimal | None = None
    max_daily_trades: int = Field(default=10, ge=1, le=100)
    max_daily_loss: Decimal = Decimal("5000.00")
    max_open_positions: int = Field(default=5, ge=1, le=50)
    max_consecutive_losses: int = 3
    # Profit cutoff settings
    max_daily_profit: Decimal | None = None
    overall_profit_target: Decimal | None = None
    profit_cutoff_action: ProfitCutoffAction = ProfitCutoffAction.PAUSE_STRATEGY
    is_paper_trading: bool = True
    product_type: StrategyProductType = StrategyProductType.DELIVERY
    # Strategy-level default fixed stop loss / take profit
    default_stop_loss_pct: Decimal | None = None
    default_take_profit_pct: Decimal | None = None
    # Strategy-level default trailing stop and profit booking settings
    default_trailing_stop_enabled: bool = False
    default_trailing_stop_pct: Decimal | None = None
    default_profit_booking_rules: ProfitBookingRules | None = None
    # Profit lock: locks stop loss at profit level once threshold is reached
    default_profit_lock_enabled: bool = False


class DSLStrategyResponse(BaseModel):
    """Response for a created DSL strategy."""

    id: str
    name: str
    description: str | None
    strategy_type: str  # Will be "dsl_<name>"
    definition: dict
    message: str


class CompositeStrategyDryRunRequest(BaseModel):
    """Request for dry-run testing a composite strategy before saving."""

    components: list[CompositeStrategyComponent] = Field(
        ..., min_length=2, max_length=5, description="2-5 component strategies to combine"
    )
    combine_logic: str = Field(
        default="AND",
        pattern="^(AND|OR|MAJORITY|WEIGHTED)$",
        description="Logic for combining signals: AND, OR, MAJORITY, or WEIGHTED",
    )
    min_agreement_pct: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Minimum agreement for MAJORITY logic"
    )
    symbol: str = Field(..., min_length=1, max_length=20, description="Symbol to test on")
    days_back: int = Field(default=90, ge=30, le=365, description="Days of historical data to test")


class CompositeStrategyDryRunResponse(BaseModel):
    """Response for composite strategy dry-run test."""

    success: bool
    symbol: str
    test_period_days: int
    total_return: float | None = None
    win_rate: float | None = None
    total_trades: int | None = None
    max_drawdown: float | None = None
    sharpe_ratio: float | None = None
    profit_factor: float | None = None
    component_signals: list[dict] | None = None  # Signal breakdown per component
    error_message: str | None = None


# ============== Auto-Trade Configuration Schemas ==============


class StrategyTemplateCreate(BaseModel):
    """Request to create a strategy template."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    strategy_type: str = Field(..., min_length=1, max_length=50)
    strategy_params: dict | None = None
    position_sizing_method: PositionSizingMethod = PositionSizingMethod.PERCENT_OF_PORTFOLIO
    position_size_value: Decimal = Field(default=Decimal("5.00"), ge=0)
    max_position_value: Decimal | None = None
    stop_loss_percent: Decimal = Field(default=Decimal("2.00"), ge=0, le=100)
    take_profit_percent: Decimal = Field(default=Decimal("4.00"), ge=0, le=100)
    max_daily_loss: Decimal = Field(default=Decimal("5000.00"), ge=0)
    max_consecutive_losses: int = Field(default=3, ge=1, le=20)
    product_type: StrategyProductType = StrategyProductType.DELIVERY
    trading_start_time: datetime | None = None
    trading_end_time: datetime | None = None
    is_default: bool = False


class StrategyTemplateUpdate(BaseModel):
    """Request to update a strategy template."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    strategy_type: str | None = Field(default=None, min_length=1, max_length=50)
    strategy_params: dict | None = None
    position_sizing_method: PositionSizingMethod | None = None
    position_size_value: Decimal | None = Field(default=None, ge=0)
    max_position_value: Decimal | None = None
    stop_loss_percent: Decimal | None = Field(default=None, ge=0, le=100)
    take_profit_percent: Decimal | None = Field(default=None, ge=0, le=100)
    max_daily_loss: Decimal | None = Field(default=None, ge=0)
    max_consecutive_losses: int | None = Field(default=None, ge=1, le=20)
    product_type: StrategyProductType | None = None
    trading_start_time: datetime | None = None
    trading_end_time: datetime | None = None
    is_default: bool | None = None
    is_active: bool | None = None


class StrategyTemplateResponse(BaseModel):
    """Response for a strategy template."""

    id: str
    user_id: str
    name: str
    description: str | None
    strategy_type: str
    strategy_params: dict | None
    position_sizing_method: PositionSizingMethod
    position_size_value: Decimal
    max_position_value: Decimal | None
    stop_loss_percent: Decimal
    take_profit_percent: Decimal
    max_daily_loss: Decimal
    max_consecutive_losses: int
    product_type: StrategyProductType
    trading_start_time: datetime | None
    trading_end_time: datetime | None
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StrategyTemplateListResponse(BaseModel):
    """Response for list of strategy templates."""

    templates: list[StrategyTemplateResponse]
    total: int


class AutoTradeConfigCreate(BaseModel):
    """Request to create an auto-trade configuration."""

    category: str = Field(..., min_length=1, max_length=50)
    enabled: bool = False
    confirmation_mode: str = Field(default="notify", pattern="^(auto|notify|disabled)$")
    strategy_template_id: str | None = None
    max_positions_per_day: int = Field(default=3, ge=1, le=20)
    max_capital_per_day: Decimal = Field(default=Decimal("50000.00"), ge=0)
    expiry_hours: int = Field(default=4, ge=1, le=24)
    weight_technical: int = Field(default=40, ge=0, le=100)
    weight_fundamental: int = Field(default=40, ge=0, le=100)
    weight_sentiment: int = Field(default=20, ge=0, le=100)
    min_confidence: str = Field(default="medium", pattern="^(high|medium|low)$")
    screener_source_type: str = Field(default="preset", pattern="^(preset|custom)$")
    preset_category: str | None = None
    saved_screener_id: str | None = None
    run_time: str | None = Field(
        default="09:20",
        description="Time to run the screener in HH:MM format (e.g., '09:20' for 9:20 AM)",
        pattern=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$",
    )
    product_type: str = Field(
        default="INTRADAY",
        pattern="^(DELIVERY|INTRADAY|MARGIN|SLB)$",
        description="Product type for created strategies",
    )
    signal_direction: str = Field(
        default="LONG",
        pattern="^(LONG|SHORT|BOTH)$",
        description="Signal direction for created strategies",
    )


class AutoTradeConfigUpdate(BaseModel):
    """Request to update an auto-trade configuration."""

    enabled: bool | None = None
    confirmation_mode: str | None = Field(default=None, pattern="^(auto|notify|disabled)$")
    strategy_template_id: str | None = None
    max_positions_per_day: int | None = Field(default=None, ge=1, le=20)
    max_capital_per_day: Decimal | None = Field(default=None, ge=0)
    expiry_hours: int | None = Field(default=None, ge=1, le=24)
    weight_technical: int | None = Field(default=None, ge=0, le=100)
    weight_fundamental: int | None = Field(default=None, ge=0, le=100)
    weight_sentiment: int | None = Field(default=None, ge=0, le=100)
    min_confidence: str | None = Field(default=None, pattern="^(high|medium|low)$")
    screener_source_type: str | None = Field(default=None, pattern="^(preset|custom)$")
    preset_category: str | None = None
    saved_screener_id: str | None = None
    run_time: str | None = Field(
        default=None,
        description="Time to run the screener in HH:MM format (e.g., '09:20' for 9:20 AM)",
        pattern=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$",
    )
    product_type: str | None = Field(
        default=None,
        pattern="^(DELIVERY|INTRADAY|MARGIN|SLB)$",
        description="Product type for created strategies",
    )
    signal_direction: str | None = Field(
        default=None,
        pattern="^(LONG|SHORT|BOTH)$",
        description="Signal direction for created strategies",
    )


class AutoTradeConfigResponse(BaseModel):
    """Response for an auto-trade configuration."""

    id: str
    user_id: str
    category: str
    enabled: bool
    confirmation_mode: str
    strategy_template_id: str | None
    max_positions_per_day: int
    max_capital_per_day: Decimal
    expiry_hours: int
    weight_technical: int
    weight_fundamental: int
    weight_sentiment: int
    min_confidence: str
    screener_source_type: str
    preset_category: str | None
    saved_screener_id: str | None
    run_time: str | None = Field(default="09:20", description="Scheduled run time in HH:MM format")
    product_type: str = Field(default="INTRADAY", description="Product type for created strategies")
    signal_direction: str = Field(
        default="LONG", description="Signal direction for created strategies"
    )
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AutoTradeConfigListResponse(BaseModel):
    """Response for list of auto-trade configurations."""

    configs: list[AutoTradeConfigResponse]
    total: int


class WeightConfigUpdate(BaseModel):
    """Request to update multi-factor weight configuration."""

    weight_technical: int = Field(..., ge=0, le=100)
    weight_fundamental: int = Field(..., ge=0, le=100)
    weight_sentiment: int = Field(..., ge=0, le=100)
    min_confidence: str = Field(default="medium", pattern="^(high|medium|low)$")


class WeightConfigResponse(BaseModel):
    """Response for weight configuration."""

    weight_technical: int
    weight_fundamental: int
    weight_sentiment: int
    min_confidence: str
    preview_symbol: str | None = None
    preview_scores: dict | None = None


class PendingAutoTradeResponse(BaseModel):
    """Response for a pending auto-trade."""

    id: str
    user_id: str
    auto_trade_config_id: str
    category: str
    recommendation_date: datetime
    symbols: list[str]
    scores: dict | None
    recommended_strategy_type: str
    suggested_params: dict | None
    status: str
    created_strategy_id: str | None
    expires_at: datetime
    actioned_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PendingAutoTradeListResponse(BaseModel):
    """Response for list of pending auto-trades."""

    pending_trades: list[PendingAutoTradeResponse]
    total: int
    pending_count: int = 0


class PendingAutoTradeAction(BaseModel):
    """Request to approve or reject a pending auto-trade."""

    action: str = Field(..., pattern="^(approve|reject)$")
    reason: str | None = Field(None, description="Optional rejection reason")


class PendingAutoTradeActionResponse(BaseModel):
    """Response after approving or rejecting a pending auto-trade."""

    id: str
    status: str
    created_strategy_id: str | None = None
    message: str

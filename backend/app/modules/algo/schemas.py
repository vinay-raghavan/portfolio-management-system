"""Pydantic schemas for algo trading module."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.modules.algo.models import (
    ExecutionStatus,
    PositionSizingMethod,
    ProfitCutoffAction,
    ScheduleType,
    StrategyProductType,
    StrategyStatus,
)
from app.modules.portfolio.schemas import ProfitBookingRules

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
    max_daily_loss: Decimal = Decimal("5000.00")
    max_consecutive_losses: int = 3
    max_daily_profit: Decimal | None = None
    overall_profit_target: Decimal | None = None
    profit_cutoff_action: ProfitCutoffAction = ProfitCutoffAction.PAUSE_STRATEGY
    is_paper_trading: bool = True
    # Product type for orders (CNC/MIS/MTF)
    product_type: StrategyProductType = StrategyProductType.DELIVERY
    # Strategy-level default trailing stop and profit booking settings
    default_trailing_stop_enabled: bool = False
    default_trailing_stop_pct: Decimal | None = None
    default_profit_booking_rules: ProfitBookingRules | None = None


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
    max_daily_loss: Decimal | None = None
    max_consecutive_losses: int | None = None
    max_daily_profit: Decimal | None = None
    overall_profit_target: Decimal | None = None
    profit_cutoff_action: ProfitCutoffAction | None = None
    is_paper_trading: bool | None = None
    # Product type for orders (CNC/MIS/MTF)
    product_type: StrategyProductType | None = None
    # Strategy-level default trailing stop and profit booking settings
    default_trailing_stop_enabled: bool | None = None
    default_trailing_stop_pct: Decimal | None = None
    default_profit_booking_rules: ProfitBookingRules | None = None


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
    max_daily_loss: Decimal
    max_consecutive_losses: int
    max_daily_profit: Decimal | None
    overall_profit_target: Decimal | None
    profit_cutoff_action: ProfitCutoffAction
    is_paper_trading: bool
    # Product type for orders (CNC/MIS/MTF)
    product_type: StrategyProductType
    # Strategy-level default trailing stop and profit booking settings
    default_trailing_stop_enabled: bool = False
    default_trailing_stop_pct: Decimal | None = None
    default_profit_booking_rules: ProfitBookingRules | None = None
    last_run_at: datetime | None
    next_run_at: datetime | None
    total_trades: int
    winning_trades: int
    total_pnl: Decimal
    created_at: datetime
    updated_at: datetime
    # Recent execution runs with order details
    recent_executions: list[RecentExecutionSummary] = []

    model_config = {"from_attributes": True}

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
            "max_daily_loss": obj.max_daily_loss,
            "max_consecutive_losses": obj.max_consecutive_losses,
            "max_daily_profit": obj.max_daily_profit,
            "overall_profit_target": obj.overall_profit_target,
            "profit_cutoff_action": obj.profit_cutoff_action,
            "is_paper_trading": obj.is_paper_trading,
            "product_type": obj.product_type,
            "default_trailing_stop_enabled": obj.default_trailing_stop_enabled,
            "default_trailing_stop_pct": obj.default_trailing_stop_pct,
            "default_profit_booking_rules": (
                ProfitBookingRules.model_validate(obj.default_profit_booking_rules)
                if obj.default_profit_booking_rules
                else None
            ),
            "last_run_at": obj.last_run_at,
            "next_run_at": obj.next_run_at,
            "total_trades": obj.total_trades,
            "winning_trades": obj.winning_trades,
            "total_pnl": obj.total_pnl,
            "created_at": obj.created_at,
            "updated_at": obj.updated_at,
            "recent_executions": recent_executions,
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
    max_daily_loss: Decimal = Decimal("5000.00")
    max_consecutive_losses: int = 3
    # Profit cutoff settings
    max_daily_profit: Decimal | None = None
    overall_profit_target: Decimal | None = None
    profit_cutoff_action: ProfitCutoffAction = ProfitCutoffAction.PAUSE_STRATEGY
    is_paper_trading: bool = True
    product_type: StrategyProductType = StrategyProductType.DELIVERY
    # Strategy-level default trailing stop and profit booking settings
    default_trailing_stop_enabled: bool = False
    default_trailing_stop_pct: Decimal | None = None
    default_profit_booking_rules: ProfitBookingRules | None = None


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
    max_daily_loss: Decimal = Decimal("5000.00")
    max_consecutive_losses: int = 3
    # Profit cutoff settings
    max_daily_profit: Decimal | None = None
    overall_profit_target: Decimal | None = None
    profit_cutoff_action: ProfitCutoffAction = ProfitCutoffAction.PAUSE_STRATEGY
    is_paper_trading: bool = True
    product_type: StrategyProductType = StrategyProductType.DELIVERY
    # Strategy-level default trailing stop and profit booking settings
    default_trailing_stop_enabled: bool = False
    default_trailing_stop_pct: Decimal | None = None
    default_profit_booking_rules: ProfitBookingRules | None = None


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

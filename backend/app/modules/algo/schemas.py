"""Pydantic schemas for algo trading module."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.modules.algo.models import (
    ExecutionStatus,
    PositionSizingMethod,
    ScheduleType,
    StrategyStatus,
)

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
    daily_loss: Decimal
    max_daily_loss: Decimal
    consecutive_losses: int
    max_consecutive_losses: int
    current_drawdown_percent: Decimal
    max_drawdown_percent: Decimal


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
    is_paper_trading: bool = True


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
    is_paper_trading: bool | None = None


class StrategyResponse(BaseModel):
    """Strategy response for router."""

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
    is_paper_trading: bool
    last_run_at: datetime | None
    next_run_at: datetime | None
    total_trades: int
    winning_trades: int
    total_pnl: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def model_validate(cls, obj, **kwargs):
        """Custom validation to map model fields to response fields."""
        if hasattr(obj, "strategy_name"):
            # It's a UserStrategy model, map fields
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
                "is_paper_trading": obj.is_paper_trading,
                "last_run_at": obj.last_run_at,
                "next_run_at": obj.next_run_at,
                "total_trades": obj.total_trades,
                "winning_trades": obj.winning_trades,
                "total_pnl": obj.total_pnl,
                "created_at": obj.created_at,
                "updated_at": obj.updated_at,
            }
            return cls(**data)
        return super().model_validate(obj, **kwargs)


class ExecutionHistoryResponse(BaseModel):
    """Execution history response."""

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

    class Config:
        from_attributes = True


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

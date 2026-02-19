"""Pydantic schemas for portfolio module."""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class ProductType(str, Enum):
    """Product type for positions."""

    DELIVERY = "DELIVERY"
    INTRADAY = "INTRADAY"


# ============== Portfolio Schemas ==============


class PortfolioCreate(BaseModel):
    """Schema for creating a portfolio."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    currency: str = Field("INR", pattern="^[A-Z]{3}$")
    is_default: bool = False


class PortfolioUpdate(BaseModel):
    """Schema for updating a portfolio."""

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    currency: str | None = Field(None, pattern="^[A-Z]{3}$")
    is_default: bool | None = None


class PortfolioInfo(BaseModel):
    """Schema for portfolio info response."""

    id: str
    name: str
    description: str | None = None
    currency: str
    is_default: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PortfolioListResponse(BaseModel):
    """Schema for list of portfolios."""

    portfolios: list[PortfolioInfo]
    total_count: int


class ProfitBookingRule(BaseModel):
    """Schema for a single profit booking rule."""

    target_pct: Decimal = Field(..., description="Target profit percentage to trigger booking")
    quantity_pct: Decimal = Field(..., description="Percentage of position to book at this level")


class ProfitBookingRules(BaseModel):
    """Schema for profit booking rules configuration."""

    enabled: bool = Field(default=True, description="Whether profit booking is enabled")
    rules: list[ProfitBookingRule] = Field(
        default_factory=list, description="List of profit booking rules"
    )
    executed: list[Decimal] = Field(
        default_factory=list, description="List of executed target percentages"
    )


class TrailingStopConfig(BaseModel):
    """Schema for trailing stop configuration response."""

    enabled: bool = Field(default=False, description="Whether trailing stop is enabled")
    percentage: Decimal | None = Field(
        None,
        ge=Decimal("0.001"),
        le=Decimal("0.50"),
        description="Trailing stop percentage (0.01 = 1%, max 50%)",
    )
    current_stop_price: Decimal | None = Field(
        None, description="Current calculated trailing stop price"
    )
    highest_price: Decimal | None = Field(
        None, description="Highest price since entry (for LONG positions)"
    )
    lowest_price: Decimal | None = Field(
        None, description="Lowest price since entry (for SHORT positions)"
    )


class TrailingStopUpdate(BaseModel):
    """Schema for updating trailing stop configuration."""

    enabled: bool = Field(..., description="Whether to enable trailing stop")
    percentage: Decimal | None = Field(
        None,
        gt=Decimal("0"),
        le=Decimal("0.50"),
        description="Trailing stop percentage (0.05 = 5%, max 50%). Required if enabled=True",
    )


class PositionResponse(BaseModel):
    """Schema for position response."""

    id: str
    portfolio_id: str | None = None
    symbol: str
    quantity: Decimal
    avg_cost: Decimal
    product_type: str = "DELIVERY"
    realized_pnl: Decimal = Decimal("0")
    current_price: Decimal | None = None
    market_value: Decimal | None = None
    unrealized_pnl: Decimal | None = None
    unrealized_pnl_pct: Decimal | None = None
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    trailing_stop: TrailingStopConfig | None = None
    profit_booking_rules: ProfitBookingRules | None = None

    model_config = {"from_attributes": True}


# ============== Funds Schemas ==============


class FundsResponse(BaseModel):
    """Schema for user funds response."""

    id: str
    user_id: str
    cash_balance: Decimal
    margin_used: Decimal
    collateral: Decimal
    available_cash: Decimal
    total_balance: Decimal
    available_margin: Decimal

    model_config = {"from_attributes": True}


class FundsUpdate(BaseModel):
    """Schema for updating funds (admin or deposit/withdraw)."""

    amount: Decimal = Field(..., description="Amount to add (positive) or withdraw (negative)")
    reason: str = Field(..., max_length=100, description="Reason for adjustment")


class FundsDepositRequest(BaseModel):
    """Schema for depositing funds."""

    amount: Decimal = Field(..., gt=0, description="Amount to deposit (must be positive)")
    note: str | None = Field(None, max_length=200, description="Optional note for the deposit")


class FundsWithdrawRequest(BaseModel):
    """Schema for withdrawing funds."""

    amount: Decimal = Field(..., gt=0, description="Amount to withdraw (must be positive)")
    note: str | None = Field(None, max_length=200, description="Optional note for the withdrawal")


class FundsResetRequest(BaseModel):
    """Schema for resetting funds to initial balance."""

    initial_balance: Decimal | None = Field(
        None, gt=0, description="Custom initial balance. Uses default if not provided."
    )


class FundsSummary(BaseModel):
    """Schema for funds summary in portfolio view."""

    cash_balance: Decimal
    margin_used: Decimal
    available_margin: Decimal
    collateral: Decimal


# ============== Daily P&L Schemas ==============


class DailyPnLResponse(BaseModel):
    """Schema for daily P&L response."""

    id: str
    date: date
    total_value: Decimal
    total_cost: Decimal
    total_pnl: Decimal
    cash_balance: Decimal
    day_pnl: Decimal
    trades_count: int

    model_config = {"from_attributes": True}


class DailyPnLHistory(BaseModel):
    """Schema for daily P&L history response."""

    records: list[DailyPnLResponse]
    total_count: int
    period_pnl: Decimal
    period_return_pct: Decimal


class TradeResponse(BaseModel):
    """Schema for trade response."""

    id: str
    portfolio_id: str | None = None
    symbol: str
    side: str
    quantity: Decimal
    price: Decimal
    fees: Decimal
    total_value: Decimal | None = None
    executed_at: datetime

    model_config = {"from_attributes": True}


class PortfolioSummary(BaseModel):
    """Schema for portfolio summary."""

    portfolio_id: str | None = None
    portfolio_name: str | None = None
    total_value: Decimal
    total_cost: Decimal
    total_pnl: Decimal
    total_pnl_pct: Decimal
    cash_balance: Decimal
    positions_count: int
    day_change: Decimal | None = None
    day_change_pct: Decimal | None = None


class PortfolioDetailResponse(BaseModel):
    """Schema for full portfolio response with positions."""

    portfolio: PortfolioInfo
    summary: PortfolioSummary
    positions: list[PositionResponse]


class PortfolioResponse(BaseModel):
    """Schema for full portfolio response (legacy, all positions)."""

    summary: PortfolioSummary
    positions: list[PositionResponse]


class TradeHistoryResponse(BaseModel):
    """Schema for trade history response."""

    trades: list[TradeResponse]
    total_count: int
    page: int
    page_size: int


# ============== Ledger Schemas ==============


class TransactionType(str, Enum):
    """Type of transaction for the ledger."""

    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    BUY = "BUY"
    SELL = "SELL"
    FEE = "FEE"
    DIVIDEND = "DIVIDEND"
    INTEREST = "INTEREST"
    ADJUSTMENT = "ADJUSTMENT"
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"


class LedgerEntryResponse(BaseModel):
    """Schema for a single ledger entry."""

    id: str
    transaction_type: str
    amount: Decimal
    running_cash_balance: Decimal
    running_margin_used: Decimal
    running_total_balance: Decimal
    reference_type: str | None = None
    reference_id: str | None = None
    symbol: str | None = None
    description: str
    extra_data: dict | None = None
    transaction_date: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class LedgerResponse(BaseModel):
    """Schema for paginated ledger response."""

    entries: list[LedgerEntryResponse]
    total_count: int
    page: int
    page_size: int
    total_in: Decimal  # Sum of credits
    total_out: Decimal  # Sum of debits (absolute value)


class LedgerStatementRequest(BaseModel):
    """Schema for requesting account statement."""

    start_date: datetime
    end_date: datetime
    transaction_types: list[TransactionType] | None = None
    symbol: str | None = None
    portfolio_id: str | None = None


class LedgerStatementSummary(BaseModel):
    """Schema for statement summary."""

    period_start: datetime
    period_end: datetime
    opening_balance: Decimal
    closing_balance: Decimal
    total_deposits: Decimal
    total_withdrawals: Decimal
    total_buys: Decimal
    total_sells: Decimal
    total_fees: Decimal
    total_dividends: Decimal
    net_change: Decimal


class LedgerStatementResponse(BaseModel):
    """Schema for full account statement."""

    summary: LedgerStatementSummary
    entries: list[LedgerEntryResponse]


class BalanceHistoryEntry(BaseModel):
    """Schema for a single balance history point."""

    date: datetime
    cash_balance: Decimal
    margin_used: Decimal
    total_balance: Decimal


class BalanceHistoryResponse(BaseModel):
    """Schema for balance history response."""

    entries: list[BalanceHistoryEntry]
    start_date: datetime
    end_date: datetime

"""Order validation service for pre-trade checks.

Validates orders before execution including:
- Market hours check
- Funds availability check
- Quantity/lot size validation
- Price circuit limits
- Position limits
"""

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.portfolio.funds_service import FundsService
from app.modules.instruments.service import InstrumentService
from app.modules.instruments.schemas import InstrumentSearchParams
from app.providers.data.factory import get_data_provider
from app.providers.schemas import OrderRequest, OrderSide

logger = logging.getLogger(__name__)


class ValidationErrorCode(str, Enum):
    """Validation error codes."""
    
    MARKET_CLOSED = "MARKET_CLOSED"
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    INVALID_QUANTITY = "INVALID_QUANTITY"
    INVALID_LOT_SIZE = "INVALID_LOT_SIZE"
    PRICE_OUTSIDE_CIRCUIT = "PRICE_OUTSIDE_CIRCUIT"
    POSITION_LIMIT_EXCEEDED = "POSITION_LIMIT_EXCEEDED"
    INVALID_SYMBOL = "INVALID_SYMBOL"
    SELL_QUANTITY_EXCEEDS_POSITION = "SELL_QUANTITY_EXCEEDS_POSITION"


@dataclass
class ValidationError:
    """A single validation error."""
    
    code: ValidationErrorCode
    message: str
    field: str | None = None


@dataclass 
class ValidationResult:
    """Result of order validation."""
    
    is_valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    
    def add_error(self, code: ValidationErrorCode, message: str, field: str | None = None):
        """Add a validation error."""
        self.errors.append(ValidationError(code=code, message=message, field=field))
        self.is_valid = False
    
    def add_warning(self, message: str):
        """Add a validation warning (doesn't fail validation)."""
        self.warnings.append(message)


class OrderValidator:
    """Service for validating orders before execution.
    
    Performs various pre-trade checks to ensure orders are valid
    and can be executed safely.
    """

    # Default circuit limit percentage (price can move +/- 20% from previous close)
    DEFAULT_CIRCUIT_LIMIT_PCT = Decimal("20")
    
    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db
        self.funds_service = FundsService(db)
        self.instrument_service = InstrumentService(db)
        self._data_provider = None

    @property
    def data_provider(self):
        """Lazy load data provider."""
        if self._data_provider is None:
            self._data_provider = get_data_provider()
        return self._data_provider

    async def validate(
        self,
        user_id: str,
        order: OrderRequest,
        skip_market_hours: bool = False,
        skip_funds_check: bool = False,
    ) -> ValidationResult:
        """Run all validations on an order.
        
        Args:
            user_id: User placing the order
            order: Order request to validate
            skip_market_hours: Skip market hours check (for testing)
            skip_funds_check: Skip funds check (for limit orders)
            
        Returns:
            ValidationResult with errors/warnings
        """
        result = ValidationResult(is_valid=True)
        
        # Get current price for calculations
        current_price = await self.data_provider.get_current_price(order.symbol)
        
        # 1. Validate symbol exists
        if not await self._validate_symbol(order.symbol, result):
            return result  # Can't continue without valid symbol
        
        # 2. Check market hours (unless skipped)
        if not skip_market_hours:
            await self._validate_market_hours(result)
        
        # 3. Check funds for BUY orders
        if order.side == OrderSide.BUY and not skip_funds_check:
            await self._validate_funds(user_id, order, current_price, result)
        
        # 4. Validate quantity
        await self._validate_quantity(order, result)
        
        # 5. Check price circuit limits (for limit orders)
        if order.price is not None and current_price is not None:
            await self._validate_circuit_limits(order, current_price, result)
        
        return result

    async def _validate_symbol(
        self, 
        symbol: str, 
        result: ValidationResult
    ) -> bool:
        """Validate symbol exists in instrument master."""
        instrument = await self.instrument_service.get_by_symbol(symbol)
        
        if instrument is None:
            # Try to get quote from data provider as fallback
            quote = await self.data_provider.get_quote(symbol)
            if quote is None:
                result.add_error(
                    ValidationErrorCode.INVALID_SYMBOL,
                    f"Symbol '{symbol}' not found",
                    "symbol"
                )
                return False
        
        return True

    async def _validate_market_hours(self, result: ValidationResult) -> bool:
        """Validate market is currently open."""
        is_open = await self.data_provider.is_market_open()

        if not is_open:
            result.add_error(
                ValidationErrorCode.MARKET_CLOSED,
                "Market is currently closed. Orders can only be placed during market hours."
            )
            return False

        return True

    async def _validate_funds(
        self,
        user_id: str,
        order: OrderRequest,
        current_price: Decimal | None,
        result: ValidationResult
    ) -> bool:
        """Validate user has sufficient funds for the order."""
        # Use order price for limit orders, current price for market orders
        price = order.price if order.price is not None else current_price

        if price is None:
            result.add_warning("Could not verify funds - price unavailable")
            return True  # Allow order to proceed, will be checked at execution

        # Calculate required amount (quantity * price + estimated fees)
        price_decimal = Decimal(str(price))
        estimated_fees = price_decimal * order.quantity * Decimal("0.001")  # 0.1% estimated fees
        required_amount = (order.quantity * price_decimal) + estimated_fees

        has_funds = await self.funds_service.check_buying_power(user_id, required_amount)

        if not has_funds:
            funds = await self.funds_service.get_or_create_funds(user_id)
            result.add_error(
                ValidationErrorCode.INSUFFICIENT_FUNDS,
                f"Insufficient funds. Required: ₹{required_amount:.2f}, "
                f"Available: ₹{funds.available_cash:.2f}",
                "quantity"
            )
            return False

        return True

    async def _validate_quantity(
        self,
        order: OrderRequest,
        result: ValidationResult
    ) -> bool:
        """Validate order quantity is valid."""
        # Check minimum quantity
        if order.quantity <= 0:
            result.add_error(
                ValidationErrorCode.INVALID_QUANTITY,
                "Quantity must be greater than 0",
                "quantity"
            )
            return False

        # Check lot size for the instrument
        instrument = await self.instrument_service.get_by_symbol(order.symbol)

        if instrument is not None and instrument.lot_size > 1:
            # Check if quantity is a multiple of lot size
            if order.quantity % instrument.lot_size != 0:
                result.add_error(
                    ValidationErrorCode.INVALID_LOT_SIZE,
                    f"Quantity must be a multiple of lot size ({instrument.lot_size})",
                    "quantity"
                )
                return False

        return True

    async def _validate_circuit_limits(
        self,
        order: OrderRequest,
        current_price: Decimal,
        result: ValidationResult
    ) -> bool:
        """Validate order price is within circuit limits."""
        # Calculate circuit limits (default +/- 20%)
        circuit_pct = self.DEFAULT_CIRCUIT_LIMIT_PCT / Decimal("100")
        lower_limit = current_price * (1 - circuit_pct)
        upper_limit = current_price * (1 + circuit_pct)

        if order.price < lower_limit or order.price > upper_limit:
            result.add_error(
                ValidationErrorCode.PRICE_OUTSIDE_CIRCUIT,
                f"Price ₹{order.price} is outside circuit limits "
                f"(₹{lower_limit:.2f} - ₹{upper_limit:.2f})",
                "price"
            )
            return False

        return True

    async def validate_sell_quantity(
        self,
        user_id: str,
        symbol: str,
        quantity: Decimal,
        result: ValidationResult
    ) -> bool:
        """Validate user has sufficient position to sell.

        Args:
            user_id: User ID
            symbol: Symbol to sell
            quantity: Quantity to sell
            result: ValidationResult to add errors to

        Returns:
            True if valid, False otherwise
        """
        from app.modules.portfolio.service import PortfolioService

        portfolio_service = PortfolioService(self.db)
        position = await portfolio_service.get_position(user_id, symbol)

        if position is None or position.quantity < quantity:
            available = position.quantity if position else Decimal("0")
            result.add_error(
                ValidationErrorCode.SELL_QUANTITY_EXCEEDS_POSITION,
                f"Cannot sell {quantity} shares. Available: {available}",
                "quantity"
            )
            return False

        return True


def create_validation_error_response(result: ValidationResult) -> dict:
    """Create API error response from validation result.

    Args:
        result: ValidationResult with errors

    Returns:
        Dict suitable for HTTPException detail
    """
    return {
        "message": "Order validation failed",
        "errors": [
            {
                "code": error.code.value,
                "message": error.message,
                "field": error.field
            }
            for error in result.errors
        ],
        "warnings": result.warnings
    }


"""Tests for LedgerService."""

from decimal import Decimal

import pytest

from app.core.security import get_password_hash
from app.modules.auth.models import User
from app.modules.portfolio.ledger_service import LedgerService
from app.modules.portfolio.models import TransactionType


class TestLedgerService:
    """Tests for LedgerService operations."""

    @pytest.fixture
    async def test_user(self, db_session):
        """Create a test user."""
        user = User(
            email="ledger_test@example.com",
            password_hash=get_password_hash("testpass123"),
            full_name="Ledger Test User",
        )
        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)
        return user

    @pytest.fixture
    def ledger_service(self, db_session):
        """Create LedgerService instance."""
        return LedgerService(db_session)

    @pytest.mark.asyncio
    async def test_record_transaction_deposit(self, ledger_service, test_user):
        """Test recording a deposit transaction."""
        entry = await ledger_service.record_transaction(
            user_id=test_user.id,
            transaction_type=TransactionType.DEPOSIT,
            amount=Decimal("100000.00"),
            description="Initial deposit",
        )

        assert entry is not None
        assert entry.user_id == test_user.id
        assert entry.transaction_type == TransactionType.DEPOSIT.value
        assert entry.amount == Decimal("100000.00")
        # running_cash_balance comes from funds table, may be 0 in test without funds setup
        assert entry.running_cash_balance is not None

    @pytest.mark.asyncio
    async def test_record_transaction_creates_entry(self, ledger_service, test_user):
        """Test that record_transaction creates a valid ledger entry."""
        entry = await ledger_service.record_transaction(
            user_id=test_user.id,
            transaction_type=TransactionType.BUY,
            amount=Decimal("-15000.00"),
            description="Buy RELIANCE",
            symbol="RELIANCE",
        )

        assert entry.id is not None
        assert entry.transaction_type == TransactionType.BUY.value
        assert entry.symbol == "RELIANCE"
        assert entry.description == "Buy RELIANCE"

    @pytest.mark.asyncio
    async def test_record_transaction_with_reference(self, ledger_service, test_user):
        """Test recording a transaction with reference to source entity."""
        from uuid import uuid4

        ref_id = str(uuid4())
        entry = await ledger_service.record_transaction(
            user_id=test_user.id,
            transaction_type=TransactionType.SELL,
            amount=Decimal("18000.00"),
            description="Sell RELIANCE",
            reference_type="trade",
            reference_id=ref_id,
        )

        assert entry.reference_type == "trade"
        assert entry.reference_id == ref_id

    @pytest.mark.asyncio
    async def test_transaction_has_transaction_date(self, ledger_service, test_user):
        """Test that transactions have a transaction date."""
        entry = await ledger_service.record_transaction(
            user_id=test_user.id,
            transaction_type=TransactionType.DEPOSIT,
            amount=Decimal("10000.00"),
            description="Deposit with date",
        )

        assert entry.transaction_date is not None

    @pytest.mark.asyncio
    async def test_transaction_types_stored_correctly(self, ledger_service, test_user):
        """Test that different transaction types are stored correctly."""
        types_to_test = [
            (TransactionType.DEPOSIT, Decimal("10000.00")),
            (TransactionType.WITHDRAWAL, Decimal("-5000.00")),
            (TransactionType.FEE, Decimal("-20.00")),
            (TransactionType.DIVIDEND, Decimal("500.00")),
        ]

        for txn_type, amount in types_to_test:
            entry = await ledger_service.record_transaction(
                user_id=test_user.id,
                transaction_type=txn_type,
                amount=amount,
                description=f"Test {txn_type.value}",
            )
            assert entry.transaction_type == txn_type.value
            assert entry.amount == amount

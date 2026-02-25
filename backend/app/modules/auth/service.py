"""Authentication service layer."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, get_password_hash, verify_password
from app.modules.auth.models import User
from app.modules.auth.schemas import TokenResponse, UserCreate
from app.modules.portfolio.funds_service import FundsService
from app.modules.portfolio.ledger_service import LedgerService

logger = logging.getLogger(__name__)


class AuthService:
    """Service class for authentication operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.ledger_service = LedgerService(db)
        self.funds_service = FundsService(db, ledger_service=self.ledger_service)

    async def get_user_by_email(self, email: str) -> User | None:
        """Get user by email address."""
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: str) -> User | None:
        """Get user by ID."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_or_create_system_user(self) -> User:
        """Get or create a system user for internal operations.

        The system user is used for automated tasks like daily recommendations,
        scheduled screeners, etc. It has a fixed email and no password.
        """
        system_email = "system@internal.local"
        user = await self.get_user_by_email(system_email)

        if user is None:
            # Create system user with a random password hash (never used for login)
            user = User(
                email=system_email,
                password_hash=get_password_hash("system-internal-never-used"),
                full_name="System",
            )
            self.db.add(user)
            await self.db.flush()
            await self.db.refresh(user)
            logger.info(f"Created system user with ID {user.id}")

        return user

    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user with initialized funds.

        Creates the user and initializes their paper trading funds
        with the configured initial balance.
        """
        user = User(
            email=user_data.email,
            password_hash=get_password_hash(user_data.password),
            full_name=user_data.full_name,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)

        # Initialize funds for the new user
        try:
            await self.funds_service.initialize_funds(user.id)
            logger.info(f"Initialized funds for new user {user.id}")
        except Exception as e:
            logger.error(f"Failed to initialize funds for user {user.id}: {e}")
            # Continue - funds can be created on first access

        return user

    async def authenticate_user(self, email: str, password: str) -> User | None:
        """Authenticate user by email and password."""
        user = await self.get_user_by_email(email)
        if user is None:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    def create_token(self, user: User) -> TokenResponse:
        """Create JWT token for user."""
        access_token = create_access_token(subject=user.id)
        return TokenResponse(access_token=access_token)

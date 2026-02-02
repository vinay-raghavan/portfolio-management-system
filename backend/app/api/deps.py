"""API dependencies for dependency injection."""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_access_token
from app.modules.auth.models import User
from app.modules.auth.service import AuthService

# Security scheme
security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)

# Internal API key for worker/service-to-service calls
INTERNAL_API_KEY = getattr(settings, "INTERNAL_API_KEY", "internal-worker-key")


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Get the current authenticated user from JWT token."""
    token = credentials.credentials
    user_id = decode_access_token(token)

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    auth_service = AuthService(db)
    user = await auth_service.get_user_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_user_optional(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(optional_security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User | None:
    """Get the current authenticated user if token is provided, else None.

    This is useful for endpoints that work for both authenticated and anonymous users,
    but provide enhanced functionality when authenticated.
    """
    if credentials is None:
        return None

    token = credentials.credentials
    user_id = decode_access_token(token)

    if user_id is None:
        return None

    auth_service = AuthService(db)
    user = await auth_service.get_user_by_id(user_id)
    return user


async def get_current_user_or_internal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(optional_security)],
    db: Annotated[AsyncSession, Depends(get_db)],
    x_internal_key: Annotated[str | None, Header()] = None,
    x_user_id: Annotated[str | None, Header()] = None,
) -> User:
    """Get the current user from JWT token OR internal API key.

    This allows both:
    1. Regular user authentication via JWT Bearer token
    2. Internal service calls via X-Internal-Key header (with optional X-User-Id)

    For internal calls, if X-User-Id is provided, returns that user.
    Otherwise, returns/creates a system user for internal operations.
    """
    # First, try internal API key authentication
    if x_internal_key:
        if x_internal_key != INTERNAL_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid internal API key",
            )

        auth_service = AuthService(db)

        # If a specific user ID is provided, use that user
        if x_user_id and x_user_id != "system":
            user = await auth_service.get_user_by_id(x_user_id)
            if user:
                return user

        # For system calls, get or create a system user
        system_user = await auth_service.get_or_create_system_user()
        return system_user

    # Fall back to JWT authentication
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    user_id = decode_access_token(token)

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    auth_service = AuthService(db)
    user = await auth_service.get_user_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


# Type aliases for cleaner dependency injection
DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_current_user_optional)]
InternalOrCurrentUser = Annotated[User, Depends(get_current_user_or_internal)]

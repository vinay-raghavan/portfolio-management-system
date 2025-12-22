"""Authentication API routes."""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.modules.auth.schemas import AuthResponse, UserCreate, UserLogin, UserResponse
from app.modules.auth.service import AuthService

router = APIRouter()


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: DbSession) -> AuthResponse:
    """Register a new user."""
    service = AuthService(db)

    # Check if user exists
    existing_user = await service.get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create user
    user = await service.create_user(user_data)
    token = service.create_token(user)

    return AuthResponse(user=UserResponse.model_validate(user), token=token)


@router.post("/login", response_model=AuthResponse)
async def login(login_data: UserLogin, db: DbSession) -> AuthResponse:
    """Login and get access token."""
    service = AuthService(db)

    user = await service.authenticate_user(login_data.email, login_data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = service.create_token(user)
    return AuthResponse(user=UserResponse.model_validate(user), token=token)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: CurrentUser) -> UserResponse:
    """Get current user information."""
    return UserResponse.model_validate(current_user)

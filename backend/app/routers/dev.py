"""Development-only router for testing and debugging.
Only available in development mode.
"""

from typing import Never

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db, get_user_service
from app.schemas.dev import DevUserCreateResponse, DevUserInfo
from app.services.user_service import UserService
from common.core.config_service import ConfigService
from common.core.jwt_utils import create_access_token
from common.utils.utils import get_logger
from shared_db.models.user import UserRole
from shared_db.schemas.user import UserResponse

logger = get_logger(__name__)
config_service = ConfigService()

# Only create router if in development mode
dev_router = APIRouter() if config_service.is_development() else None


class DevTokenRequest(BaseModel):
    """Request schema for creating development tokens"""

    username: str
    email: str | None = None
    user_sub: str | None = None
    expires_in: int | None = 7200  # 2 hours default


class DevTokenResponse(BaseModel):
    """Response schema for development tokens"""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


def check_development_mode() -> None:
    """Dependency to ensure endpoint is only available in development"""
    if not config_service.is_development():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Development endpoints not available in production",
        )


if dev_router is not None:

    @dev_router.post("/create-token", response_model=DevTokenResponse)
    async def create_dev_token(
        request: DevTokenRequest,
        db: AsyncSession = Depends(get_db),
        user_service: UserService = Depends(get_user_service),
        _: None = Depends(check_development_mode),
        _current_user: UserResponse = Depends(get_current_user),
    ) -> DevTokenResponse:
        """Create a local development token for testing API endpoints.
        Only available in development mode.
        """
        try:
            # Check if user exists in database
            user = await user_service.get_user_by_username(db, username=request.username)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User '{request.username}' not found in database",
                )

            # Create token data
            token_data = {
                "username": request.username,
                "email": request.email or user.email,
                "user_sub": request.user_sub,
            }

            # Create the token
            access_token = create_access_token(
                data=token_data,
                expires_delta=request.expires_in,
            )

            logger.info(f"Created development token for user: {request.username}")

            return DevTokenResponse(
                access_token=access_token,
                expires_in=request.expires_in or 30,
            )

        except Exception as e:
            logger.exception("Failed to create development token")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create token: {e!s}",
            ) from e

    @dev_router.get("/users")
    async def list_dev_users(
        db: AsyncSession = Depends(get_db),
        user_service: UserService = Depends(get_user_service),
        _: None = Depends(check_development_mode),
        _current_user: UserResponse = Depends(get_current_user),
    ) -> list[DevUserInfo]:
        """List all users for development token creation.
        Only available in development mode.
        """
        try:
            users = await user_service.get_users(db, skip=0, limit=100)
            return [
                DevUserInfo(
                    username=user.username,
                    email=user.email,
                    role=user.role.value,
                    is_active=user.is_active,
                )
                for user in users
            ]
        except Exception as e:
            logger.exception("Failed to list users")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to list users: {e!s}",
            ) from e

    @dev_router.post("/create-test-user")
    async def create_test_user(
        db: AsyncSession = Depends(get_db),
        user_service: UserService = Depends(get_user_service),
        _: None = Depends(check_development_mode),
        _current_user: UserResponse = Depends(get_current_user),
    ) -> DevUserCreateResponse:
        """Create a test user for development.
        Only available in development mode.
        """
        try:
            # Check if test user already exists
            existing_user = await user_service.get_user_by_username(db, username="testuser")
            if existing_user:
                return DevUserCreateResponse(
                    message="Test user already exists",
                    username=existing_user.username,
                    email=existing_user.email,
                    role=existing_user.role.value,
                )

            # Create test user using UserService
            test_user = await user_service.create_user_from_params(
                db=db,
                username="testuser",
                email="test@example.com",
                full_name="Test User",
                role=UserRole.USER,
            )

            logger.info("Created test user for development")

            return DevUserCreateResponse(
                message="Test user created successfully",
                username=test_user.username,
                email=test_user.email,
                role=test_user.role.value,
            )

        except Exception as e:
            logger.exception("Failed to create test user")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create test user: {e!s}",
            ) from e

else:
    # Create empty router for production
    dev_router = APIRouter()

    @dev_router.get("/", response_model=None)
    async def dev_not_available() -> Never:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Development endpoints not available in production",
        )

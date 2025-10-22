"""User service layer for business logic operations."""

from sqlalchemy.ext.asyncio import AsyncSession

from common.ids import UserId
from common.utils.utils import get_logger
from shared_db.crud.user import UserDAO
from shared_db.models.user import AvatarType, UserRole
from shared_db.schemas.user import CoinConsumeFailureReason, CoinConsumptionResult, UserCreate, UserResponse, UserUpdate

logger = get_logger()


class UserService:
    """Service layer for user operations.
    Handles business logic and coordinates between routers and DAOs.
    """

    def __init__(self, user_dao: UserDAO) -> None:
        """Initialize UserService with UserDAO dependency.

        Args:
            user_dao: UserDAO instance for database operations
        """
        self.user_dao = user_dao

    async def add_coins(self, db: AsyncSession, user_id: UserId, coins: int) -> UserResponse | None:
        """Atomically add coins to a user's balance."""
        logger.info(f"Adding {coins} coins to user {user_id}")
        return await self.user_dao.add_coins(db, user_id, coins)

    async def get_user_by_id(self, db: AsyncSession, user_id: UserId) -> UserResponse | None:
        """Get a user by ID.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            UserResponse if found, None otherwise
        """
        logger.info(f"Getting user by ID: {user_id}")
        return await self.user_dao.get(db, user_id)

    async def get_users(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> list[UserResponse]:
        """Get multiple users with pagination.

        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of UserResponse objects
        """
        logger.info(f"Getting users with skip={skip}, limit={limit}")
        return await self.user_dao.get_multi(db, skip=skip, limit=limit)

    async def get_user_by_email(self, db: AsyncSession, email: str) -> UserResponse | None:
        """Get a user by email address.

        Args:
            db: Database session
            email: User email address

        Returns:
            UserResponse if found, None otherwise
        """
        logger.info(f"Getting user by email: {email}")
        return await self.user_dao.get_by_email(db, email)

    async def get_user_by_username(self, db: AsyncSession, username: str) -> UserResponse | None:
        """Get a user by username.

        Args:
            db: Database session
            username: Username

        Returns:
            UserResponse if found, None otherwise
        """
        logger.info(f"Getting user by username: {username}")
        return await self.user_dao.get_by_username(db, username)

    async def get_user_by_cognito_sub(self, db: AsyncSession, cognito_sub: str) -> UserResponse | None:
        """Get a user by Cognito sub (user ID).

        Args:
            db: Database session
            cognito_sub: Cognito user ID

        Returns:
            UserResponse if found, None otherwise
        """
        logger.debug(f"Getting user by Cognito sub: {cognito_sub}")
        return await self.user_dao.get_by_cognito_sub(db, cognito_sub)

    async def create_user(self, db: AsyncSession, user_create: UserCreate) -> UserResponse:
        """Create a new user.

        Args:
            db: Database session
            user_create: User creation data

        Returns:
            Created UserResponse
        """
        logger.info(f"Creating user: {user_create.username}")
        return await self.user_dao.create(db, obj_in=user_create)

    async def create_user_from_params(
        self,
        db: AsyncSession,
        username: str,
        email: str,
        full_name: str | None = None,
        role: UserRole = UserRole.USER,
        cognito_sub: str | None = None,
        avatar_url: str | None = None,
        avatar_type: AvatarType | None = AvatarType.DEFAULT,
    ) -> UserResponse:
        """Create a user from individual parameters (legacy support).

        Args:
            db: Database session
            username: Username
            email: Email address
            full_name: Full name (optional)
            role: User role
            cognito_sub: Cognito user ID (optional)

        Returns:
            Created UserResponse
        """
        logger.info(f"Creating user from params: {username}")
        return await self.user_dao.create_user_legacy(
            db,
            username,
            email,
            full_name,
            role,
            cognito_sub,
            avatar_url,
            avatar_type,
        )

    async def update_user(self, db: AsyncSession, user_id: UserId, user_update: UserUpdate) -> UserResponse | None:
        """Update a user by ID.

        Args:
            db: Database session
            user_id: User ID
            user_update: User update data

        Returns:
            Updated UserResponse if found, None otherwise
        """
        logger.info(f"Updating user: {user_id}")
        return await self.user_dao.update_by_id(db, user_id, user_update)

    async def delete_user(self, db: AsyncSession, user_id: UserId) -> bool:
        """Delete a user by ID.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            True if deleted, False if not found
        """
        logger.info(f"Deleting user: {user_id}")
        return await self.user_dao.delete(db, id=user_id)

    async def delete_user_with_cascade(self, db: AsyncSession, user_id: UserId) -> bool:
        """Delete a user by ID with cascading to all related records.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            True if deleted, False if not found
        """
        logger.info(f"Deleting user with cascade: {user_id}")
        return await self.user_dao.delete_with_cascade(db, id=user_id)

    async def get_user_count(self, db: AsyncSession) -> int:
        """Get the total number of users.

        Args:
            db: Database session

        Returns:
            Total number of users
        """
        logger.info("Getting user count")
        return await self.user_dao.get_count(db)

    async def is_first_user(self, db: AsyncSession) -> bool:
        """Check if this would be the first user in the system.

        Args:
            db: Database session

        Returns:
            True if no users exist, False otherwise
        """
        return await self.get_user_count(db) == 0

    async def try_consume_coins(self, db: AsyncSession, user_id: UserId, coins: int) -> CoinConsumptionResult:
        """Attempt to consume coins; returns success flag and new balance.
        Delegates to DAO for atomicity (row lock + conditional update).
        Never raises on user/amount/balance errors; maps unexpected errors to INTERNAL_ERROR.
        """
        logger.info(f"Consuming {coins} coins for user {user_id}")
        try:
            return await self.user_dao.try_consume_coins(db, user_id, coins)
        except Exception:
            logger.exception("try_consume_coins failed")
            return CoinConsumptionResult(successful=False, new_balance=0, reason=CoinConsumeFailureReason.INTERNAL_ERROR)

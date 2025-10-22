from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.ids import UserId
from shared_db.models.user import AvatarType, User, UserRole
from shared_db.schemas.user import (
    CoinConsumeFailureReason,
    CoinConsumptionResult,
    UserCreate,
    UserResponse,
    UserUpdate,
)


class UserDAO:
    """Data Access Object for User operations.
    Returns Pydantic objects instead of SQLAlchemy models.
    """

    def __init__(self) -> None:
        pass

    async def get(self, db: AsyncSession, id: UserId) -> UserResponse | None:
        """Get a user by ID."""
        result = await db.execute(select(User).where(User.id == id))
        user = result.scalar_one_or_none()
        return UserResponse.model_validate(user) if user else None

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[UserResponse]:
        """Get multiple users with pagination."""
        result = await db.execute(select(User).offset(skip).limit(limit))
        users = result.scalars().all()
        return [UserResponse.model_validate(user) for user in users]

    async def get_by_email(self, db: AsyncSession, email: str) -> UserResponse | None:
        """Get a user by email."""
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        return UserResponse.model_validate(user) if user else None

    async def get_by_username(self, db: AsyncSession, username: str) -> UserResponse | None:
        """Get a user by username."""
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        return UserResponse.model_validate(user) if user else None

    async def get_by_cognito_sub(
        self,
        db: AsyncSession,
        cognito_sub: str,
    ) -> UserResponse | None:
        """Get a user by Cognito sub (user ID)."""
        result = await db.execute(select(User).where(User.cognito_sub == cognito_sub))
        user = result.scalar_one_or_none()
        return UserResponse.model_validate(user) if user else None

    async def create(self, db: AsyncSession, *, obj_in: UserCreate, **_kwargs: Any) -> UserResponse:
        """Create a new user."""
        # Check if this is the first user (make them admin)
        result = await db.execute(select(func.count(User.id)))
        user_count = result.scalar()
        role = UserRole.ADMIN if user_count == 0 else obj_in.role

        # Set initial token balance - use provided value or default to 1000
        initial_balance = obj_in.coins_balance if obj_in.coins_balance is not None else 1000

        user = User(
            username=obj_in.username,
            email=obj_in.email,
            full_name=obj_in.full_name,
            nickname=getattr(obj_in, "nickname", None),
            role=role,
            cognito_sub=obj_in.cognito_sub,
            coins_balance=initial_balance,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return UserResponse.model_validate(user)

    async def update(self, db: AsyncSession, *, db_obj: User, obj_in: UserUpdate) -> UserResponse:
        """Update an existing user."""
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        await db.commit()
        await db.refresh(db_obj)
        return UserResponse.model_validate(db_obj)

    async def update_by_id(
        self,
        db: AsyncSession,
        user_id: UserId,
        obj_in: UserUpdate,
    ) -> UserResponse | None:
        """Update a user by ID."""
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return None
        return await self.update(db, db_obj=user, obj_in=obj_in)

    async def delete(self, db: AsyncSession, *, id: UserId) -> bool:
        """Delete a user by ID."""
        result = await db.execute(select(User).where(User.id == id))
        user = result.scalar_one_or_none()
        if not user:
            return False

        await db.delete(user)
        await db.commit()
        return True

    async def delete_with_cascade(self, db: AsyncSession, *, id: UserId) -> bool:
        """Delete a user by ID with cascading to all related records."""
        result = await db.execute(select(User).where(User.id == id))
        user = result.scalar_one_or_none()
        if not user:
            return False

        # SQLAlchemy cascade relationships are defined in the model
        # The User model has cascade relationships that will automatically delete:
        # - LLMIntegration, Tool, Agent, and all their related records
        await db.delete(user)
        await db.commit()
        return True

    async def get_count(self, db: AsyncSession) -> int:
        """Get the total number of users."""
        result = await db.execute(select(func.count(User.id)))
        return result.scalar() or 0

    async def add_coins(self, db: AsyncSession, user_id: UserId, coins: int) -> UserResponse | None:
        """Atomically add coins to a user's balance and return the updated user."""
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return None
        user.coins_balance = int(user.coins_balance or 0) + int(coins)
        await db.commit()
        await db.refresh(user)
        return UserResponse.model_validate(user)

    async def try_consume_coins(self, db: AsyncSession, user_id: UserId, coins: int) -> CoinConsumptionResult:
        """Atomically consume coins if sufficient balance.
        Returns CoinConsumptionResult with success flag and new balance.
        """
        if coins <= 0:
            # No-op for non-positive consumption
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            current = int(user.coins_balance or 0) if user else 0
            return CoinConsumptionResult(successful=False, new_balance=current, reason=CoinConsumeFailureReason.INVALID_AMOUNT)

        # Lock the row to avoid race conditions
        result = await db.execute(select(User).where(User.id == user_id).with_for_update())
        user = result.scalar_one_or_none()
        if not user:
            return CoinConsumptionResult(successful=False, new_balance=0, reason=CoinConsumeFailureReason.USER_NOT_FOUND)

        current_balance = int(user.coins_balance or 0)
        if current_balance < coins:
            return CoinConsumptionResult(successful=False, new_balance=current_balance, reason=CoinConsumeFailureReason.INSUFFICIENT_FUNDS)

        user.coins_balance = current_balance - int(coins)
        await db.commit()
        await db.refresh(user)
        return CoinConsumptionResult(successful=True, new_balance=int(user.coins_balance or 0))

    async def create_user_legacy(
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
        """Legacy method for creating a user with individual parameters.
        Use create() with UserCreate schema instead.
        """
        user_create = UserCreate(
            username=username,
            email=email,
            full_name=full_name,
            nickname=None,
            role=role,
            cognito_sub=cognito_sub,
            avatar_url=avatar_url,
            avatar_type=avatar_type,
        )
        return await self.create(db, obj_in=user_create)

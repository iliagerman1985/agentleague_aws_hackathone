"""User schemas for shared database operations."""

from enum import StrEnum

from pydantic import ConfigDict, EmailStr

from common.ids import UserId
from common.utils.json_model import JsonModel
from shared_db.models.user import AvatarType, UserRole


class UserBase(JsonModel):
    """Base user schema with common fields."""

    username: str
    email: EmailStr
    full_name: str | None = None
    nickname: str | None = None
    coins_balance: int | None = None
    avatar_url: str | None = None
    avatar_type: AvatarType | None = AvatarType.DEFAULT


class UserCreate(UserBase):
    """Schema for creating a new user."""

    role: UserRole | None = UserRole.USER
    cognito_sub: str | None = None


class UserUpdate(UserBase):
    """Schema for updating a user."""

    username: str | None = None
    email: EmailStr | None = None
    full_name: str | None = None
    is_active: bool | None = None
    role: UserRole | None = None
    cognito_sub: str | None = None
    avatar_url: str | None = None
    avatar_type: AvatarType | None = None


class UserResponse(UserBase):
    """Schema for user responses."""

    id: UserId
    is_active: bool
    role: UserRole
    cognito_sub: str | None = None

    model_config = ConfigDict(from_attributes=True)


class UserInDB(UserResponse):
    """Schema for user data as stored in database."""


class CoinConsumeFailureReason(StrEnum):
    """Failure reasons for coin consumption attempts."""

    INSUFFICIENT_FUNDS = "insufficient_funds"
    USER_NOT_FOUND = "user_not_found"
    INVALID_AMOUNT = "invalid_amount"
    INTERNAL_ERROR = "internal_error"


class CoinConsumptionResult(JsonModel):
    """Result of attempting to consume coins from a user's balance."""

    successful: bool
    new_balance: int
    reason: CoinConsumeFailureReason | None = None

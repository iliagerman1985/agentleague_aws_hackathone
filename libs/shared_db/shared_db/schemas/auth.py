"""Authentication schemas for API requests and responses."""

from pydantic import BaseModel, EmailStr, Field

from common.utils.json_model import JsonModel
from shared_db.models.user import AvatarType, UserRole


class SignUpRequest(BaseModel):
    """Request schema for user sign up"""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    password_confirmation: str = Field(..., min_length=8, max_length=128)
    first_name: str = Field(..., max_length=50)  # Will be combined with last_name to create full_name
    last_name: str = Field(..., max_length=50)  # Will be combined with first_name to create full_name


class SignUpResponse(JsonModel):
    """Response schema for user sign up"""

    message: str
    user_sub: str
    user_confirmed: bool


class ConfirmSignUpRequest(BaseModel):
    """Request schema for confirming user sign up"""

    email: EmailStr
    confirmation_code: str = Field(..., min_length=6, max_length=6)


class ConfirmSignUpResponse(JsonModel):
    """Response schema for confirming user sign up"""

    message: str


class SignInRequest(BaseModel):
    """Request schema for user sign in"""

    email: EmailStr
    password: str


class SignInResponse(JsonModel):
    """Response schema for user sign in"""

    access_token: str
    id_token: str
    refresh_token: str | None
    expires_in: int
    token_type: str = "Bearer"
    user: "UserInfo"


class RefreshTokenRequest(BaseModel):
    """Request schema for refreshing access token"""

    refresh_token: str
    email: EmailStr


class RefreshTokenResponse(JsonModel):
    """Response schema for refreshing access token"""

    access_token: str
    id_token: str
    expires_in: int
    token_type: str = "Bearer"


class UserInfo(JsonModel):
    """User information schema (camelCase JSON via JsonModel)"""

    username: str
    email: str
    full_name: str | None = None
    nickname: str | None = None
    # display_name is a convenience field clients can use directly
    display_name: str | None = None
    family_name: str | None = None
    role: UserRole
    is_active: bool
    coins_balance: int | None = None
    user_sub: str | None = None
    avatar_url: str | None = None
    avatar_type: AvatarType | None = AvatarType.DEFAULT


class TokenData(BaseModel):
    """Token data schema for JWT validation"""

    username: str | None = None
    user_sub: str | None = None
    email: str | None = None


class PasswordChangeRequest(BaseModel):
    """Request schema for changing password"""

    old_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class PasswordResetRequest(BaseModel):
    """Request schema for password reset"""

    username: str


class PasswordResetResponse(JsonModel):
    """Response schema for password reset"""

    message: str


class MessageResponse(JsonModel):
    """Generic message response schema"""

    message: str


class OAuthCallbackRequest(BaseModel):
    """Request schema for OAuth callback handling"""

    code: str = Field(..., description="Authorization code from OAuth provider")
    state: str | None = Field(default=None, description="State parameter for CSRF protection")


class OAuthUrlResponse(JsonModel):
    """Response schema for OAuth URL generation"""

    oauth_url: str = Field(..., description="URL to redirect user to for OAuth authentication")
    state: str = Field(..., description="State parameter for CSRF protection")


class DeleteAccountRequest(BaseModel):
    """Request schema for deleting user account"""

    password: str = Field(..., description="Current password for verification")


class DeleteAccountResponse(JsonModel):
    """Response schema for deleting user account"""

    message: str
    success: bool

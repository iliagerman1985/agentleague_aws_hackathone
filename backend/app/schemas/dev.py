"""Development-only schemas."""

from pydantic import BaseModel, Field

from common.utils.json_model import JsonModel


class DevUserInfo(BaseModel):
    """Development user information."""

    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    role: str = Field(..., description="User role")
    is_active: bool = Field(..., description="Whether user is active")


class DevUserCreateResponse(JsonModel):
    """Response for dev user creation."""

    message: str = Field(..., description="Status message")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    role: str | None = Field(None, description="User role")

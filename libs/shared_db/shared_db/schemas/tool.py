"""Tool schemas for API requests and responses."""

from datetime import datetime

from game_api import GameType
from pydantic import BaseModel, ConfigDict, Field

from common.ids import ToolId
from common.utils.json_model import JsonModel
from shared_db.models.tool import ToolValidationStatus


class ToolBase(JsonModel):
    """Base tool schema with common fields."""

    display_name: str = Field(..., min_length=1, max_length=150, description="User-facing display name")
    description: str | None = Field(default=None, description="Tool description")
    code: str = Field(..., min_length=1, description="Python code for the tool")
    environment: GameType = Field(..., description="Game environment this tool is designed for")
    validation_status: ToolValidationStatus = Field(
        default=ToolValidationStatus.VALID,
        description="Current validation status of the tool",
    )


class ToolCreate(ToolBase):
    """Schema for creating a new tool."""


class ToolUpdate(BaseModel):
    """Schema for updating a tool."""

    display_name: str | None = Field(default=None, min_length=1, max_length=150, description="User-facing display name")
    description: str | None = Field(default=None, description="Tool description")
    code: str | None = Field(default=None, min_length=1, description="Python code for the tool")
    environment: GameType | None = Field(default=None, description="Game environment this tool is designed for")


class ToolResponse(ToolBase):
    """Schema for tool responses."""

    model_config = ConfigDict(from_attributes=True)

    id: ToolId
    # Machine-readable snake_case name used in agent tool calls
    name: str
    created_at: datetime
    updated_at: datetime
    # System tool flag
    is_system: bool = Field(default=False, description="Whether this is a system-wide tool available to all users")


class ToolStatusUpdateRequest(BaseModel):
    """Request to update a tool's validation status."""

    validation_status: ToolValidationStatus


class ToolStatusResponse(JsonModel):
    """Response containing the validation status for a tool."""

    tool_id: ToolId
    validation_status: ToolValidationStatus
    updated_at: datetime


class ToolInDB(ToolResponse):
    """Schema for tool data as stored in database."""

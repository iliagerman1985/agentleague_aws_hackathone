"""Avatar-related schemas."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from common.ids import AgentId, AgentVersionId
from common.utils.json_model import JsonModel


class Theme(StrEnum):
    """Theme options for avatar background."""

    LIGHT = "light"
    DARK = "dark"


class CropData(BaseModel):
    """Crop data for avatar images."""

    x: float = Field(..., description="X coordinate of crop area (top-left corner)")
    y: float = Field(..., description="Y coordinate of crop area (top-left corner)")
    size: float = Field(..., description="Size of the crop area (width and height)")
    scale: float = Field(..., description="Scale factor applied to the image")


class AvatarUploadResponse(JsonModel):
    """Response for avatar upload operations."""

    message: str = Field(..., description="Success message")
    avatar_url: str = Field(..., description="URL of the uploaded avatar")


class AvatarResponse(JsonModel):
    """Response for avatar retrieval operations."""

    avatar_url: str = Field(..., description="URL of the avatar")
    avatar_type: str = Field(..., description="Type of avatar (default, uploaded, etc.)")


class BatchAgentAvatarRequest(BaseModel):
    """Request payload to fetch multiple agent avatars by version IDs."""

    agent_version_ids: list[AgentVersionId] = Field(..., description="List of agent version IDs")


class AgentAvatarInfo(JsonModel):
    """Avatar info for an agent version."""

    agent_version_id: AgentVersionId = Field(..., description="Agent version ID")
    agent_id: AgentId = Field(..., description="Agent ID")
    avatar_url: str | None = Field(None, description="Avatar URL (data URL or static URL)")
    avatar_type: str | None = Field(None, description="Avatar type (default, uploaded, google)")


class BatchAgentAvatarResponse(JsonModel):
    """Response containing avatars for multiple agent versions."""

    avatars: list[AgentAvatarInfo] = Field(default_factory=list)

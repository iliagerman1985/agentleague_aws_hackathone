"""Pydantic schemas for error report persistence."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from common.ids import ErrorReportId, UserId
from common.utils.json_model import JsonModel


class ErrorReportCreate(BaseModel):
    """Payload for creating a new error report."""

    message: str = Field(..., min_length=1, description="Primary error message shown to the user")
    name: str | None = Field(default=None, description="Error name or type, if available")
    stack: str | None = Field(default=None, description="Full JavaScript stack trace")
    component_stack: str | None = Field(default=None, description="React component stack trace")
    url: str | None = Field(default=None, description="Browser URL where the error occurred")
    user_agent: str | None = Field(default=None, description="Navigator user agent string")
    metadata: dict[str, Any] | None = Field(default=None, description="Additional context sent by the client")


class ErrorReportUserDetails(BaseModel):
    """Subset of user information to persist with an error report."""

    id: UserId | None = Field(default=None, description="TSID of the user if available")
    email: str | None = Field(default=None, description="User email at time of error")
    username: str | None = Field(default=None, description="Username at time of error")
    full_name: str | None = Field(default=None, description="Full name at time of error")
    role: str | None = Field(default=None, description="Role at time of error")


class ErrorReportResponse(JsonModel):
    """Serialized error report as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: ErrorReportId
    user_id: UserId | None = None
    user_email: str | None = None
    user_username: str | None = None
    user_full_name: str | None = None
    user_role: str | None = None
    created_at: datetime
    updated_at: datetime

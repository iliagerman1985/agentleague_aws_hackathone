"""Agent metadata schemas."""

from typing import Any

from pydantic import Field

from common.utils.json_model import JsonModel


class EnvironmentsMetadataResponse(JsonModel):
    """Response containing metadata for all game environments."""

    environments: dict[str, dict[str, Any]] = Field(..., description="Environment metadata keyed by environment type")

"""Health check schemas."""

from pydantic import Field

from common.utils.json_model import JsonModel


class HealthCheckResponse(JsonModel):
    """Health check response."""

    status: str = Field(..., description="Service health status")
    service: str = Field(..., description="Service name")
    environment: str = Field(..., description="Environment name")
    use_mock_cognito: bool = Field(..., description="Whether mock Cognito is enabled")
    is_testing: bool = Field(..., description="Whether in testing mode")
    database_type: str = Field(..., description="Database type (sqlite/postgresql)")

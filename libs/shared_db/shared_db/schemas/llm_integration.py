"""LLM Integration schemas for API requests and responses."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from common.enums import LLMProvider
from common.ids import LLMIntegrationId, UserId
from common.utils.json_model import JsonModel
from shared_db.models.llm_enums import AnthropicModel, AWSBedrockModel, GoogleModel, LLMModelType, OpenAIModel


class LLMIntegrationBase(JsonModel):
    """Base LLM integration schema with common fields."""

    provider: LLMProvider
    selected_model: LLMModelType  # Type-safe model selection
    display_name: str | None = None
    is_active: bool = True


class LLMIntegrationCreate(LLMIntegrationBase):
    """Schema for creating a new LLM integration."""

    api_key: str = Field(..., description="Plain text API key (will be encrypted)")
    is_default: bool = False

    @field_validator("selected_model")
    @classmethod
    def validate_model_for_provider(cls, v: LLMModelType, info: Any) -> LLMModelType:
        """Validate that the selected model is valid for the provider."""
        if "provider" not in info.data:
            return v

        provider: LLMProvider = info.data["provider"]

        # Check if the model belongs to the correct provider's enum
        if provider == LLMProvider.OPENAI and not isinstance(v, OpenAIModel):
            raise ValueError(f"Model '{v}' is not a valid OpenAI model")
        if provider == LLMProvider.ANTHROPIC and not isinstance(v, AnthropicModel):
            raise ValueError(f"Model '{v}' is not a valid Anthropic model")
        if provider == LLMProvider.GOOGLE and not isinstance(v, GoogleModel):
            raise ValueError(f"Model '{v}' is not a valid Google model")
        if provider == LLMProvider.AWS_BEDROCK and not isinstance(v, AWSBedrockModel):
            raise ValueError(f"Model '{v}' is not a valid AWS Bedrock model")
        if provider not in [LLMProvider.OPENAI, LLMProvider.ANTHROPIC, LLMProvider.GOOGLE, LLMProvider.AWS_BEDROCK]:
            raise ValueError(f"Unsupported provider: {provider}")

        return v


class LLMIntegrationUpdate(BaseModel):
    """Schema for updating an LLM integration."""

    selected_model: LLMModelType | None = None
    display_name: str | None = None
    is_active: bool | None = None
    api_key: str | None = Field(default=None, description="Plain text API key (will be encrypted)")

    @field_validator("selected_model")
    @classmethod
    def validate_model_if_provided(cls, v: LLMModelType | None) -> LLMModelType | None:
        """Validate model if provided (provider validation needs to be done in service layer)."""
        return v


class LLMIntegrationResponse(LLMIntegrationBase):
    """Schema for LLM integration responses (excludes API key for security)."""

    model_config = ConfigDict(from_attributes=True)

    id: LLMIntegrationId
    user_id: UserId
    is_default: bool
    created_at: datetime
    updated_at: datetime


class LLMIntegrationWithKey(LLMIntegrationResponse):
    """Schema for internal use that includes the decrypted API key."""

    api_key: str = Field(..., description="Decrypted API key for internal use only")


class LLMModelInfo(BaseModel):
    """Schema for LLM model information."""

    model_id: str
    display_name: str
    description: str
    context_window: int
    supports_tools: bool
    supports_vision: bool
    input_price_per_1m: float
    output_price_per_1m: float


class LLMProviderModels(JsonModel):
    """Schema for provider models response."""

    provider: LLMProvider
    models: list[LLMModelInfo]


class LLMTestRequest(BaseModel):
    """Schema for testing LLM integration."""

    test_prompt: str = Field(default="Hello, please respond with 'API connection successful'")


class LLMApiKeyTestRequest(BaseModel):
    """Schema for testing API key directly."""

    provider: LLMProvider
    api_key: str
    model: LLMModelType
    test_prompt: str = Field(default="Hello, please respond with 'API connection successful'")


class LLMTestResponse(JsonModel):
    """Schema for LLM test response."""

    success: bool
    response_text: str | None = None
    error_message: str | None = None
    latency_ms: int | None = None


class SetDefaultRequest(BaseModel):
    """Schema for setting default integration."""

    # No additional fields needed, just the integration ID from URL


# Export schemas for easier importing
__all__ = [
    "LLMApiKeyTestRequest",
    "LLMIntegrationBase",
    "LLMIntegrationCreate",
    "LLMIntegrationResponse",
    "LLMIntegrationUpdate",
    "LLMIntegrationWithKey",
    "LLMModelInfo",
    "LLMModelType",
    "LLMProviderModels",
    "LLMTestRequest",
    "LLMTestResponse",
    "SetDefaultRequest",
]

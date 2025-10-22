"""Pydantic models for LLM provider configurations and information."""

from pydantic import BaseModel, ConfigDict, Field

from common.enums import LLMProvider


class ProviderConfigData(BaseModel):
    """Flexible Pydantic model for provider configuration data."""

    model_config = ConfigDict(extra="allow")  # Allow additional provider-specific fields

    # Common fields (optional to handle different provider schemas)
    api_key: str | None = Field(default=None, description="API key for the provider")
    base_url: str | None = Field(default=None, description="Base URL for the provider API")
    timeout: int = Field(30, description="Request timeout in seconds")
    max_retries: int = Field(3, description="Maximum number of retries")

    # OpenAI specific fields
    organization: str | None = Field(default=None, description="OpenAI organization ID")

    # Azure OpenAI specific fields
    deployment_name: str | None = Field(default=None, description="Azure deployment name")
    api_version: str | None = Field(default=None, description="Azure API version")

    # AWS Bedrock specific fields
    aws_access_key_id: str | None = Field(default=None, description="AWS access key ID")
    aws_secret_access_key: str | None = Field(default=None, description="AWS secret access key")
    aws_region: str | None = Field(default=None, description="AWS region")
    aws_session_token: str | None = Field(default=None, description="AWS session token")

    # Google specific fields
    project_id: str | None = Field(default=None, description="Google Cloud project ID")
    location: str | None = Field(default=None, description="Google Cloud location")


class ProviderInfo(BaseModel):
    """Pydantic model for provider information."""

    name: str = Field(..., description="Provider name")
    service_class: str = Field(..., description="Service class name")
    is_supported: bool = Field(..., description="Whether provider is supported")
    is_configured: bool = Field(..., description="Whether provider is configured")
    is_available: bool = Field(..., description="Whether provider service is available")
    config: ProviderConfigData | None = Field(default=None, description="Provider configuration")
    supported_models: list[str] = Field(default_factory=list, description="List of supported models")


class ProviderErrorInfo(BaseModel):
    """Pydantic model for provider error information."""

    error: str = Field(..., description="Error message")
    error_type: str = Field(..., description="Type of error")


class ServiceFactoryInfo(BaseModel):
    """Pydantic model for service factory information."""

    total_providers: int = Field(..., description="Total number of registered providers")
    available_providers: int = Field(..., description="Number of available providers")
    configured_providers: int = Field(..., description="Number of configured providers")
    base_service_available: bool = Field(..., description="Whether base service is available")


class ProviderTestResult(BaseModel):
    """Pydantic model for provider test results."""

    provider: LLMProvider = Field(..., description="Provider that was tested")
    success: bool = Field(..., description="Whether the test was successful")
    response_text: str | None = Field(default=None, description="Response from the test")
    latency_ms: int | None = Field(default=None, description="Response latency in milliseconds")
    error_message: str | None = Field(default=None, description="Error message if test failed")
    model_used: str | None = Field(default=None, description="Model used for the test")


class ModelInfo(BaseModel):
    """Pydantic model for model information."""

    model_id: str = Field(..., description="Model identifier")
    display_name: str = Field(..., description="Human-readable model name")
    provider: LLMProvider = Field(..., description="Provider that offers this model")
    description: str = Field(..., description="Model description")
    context_window: int = Field(..., description="Context window size")
    supports_tools: bool = Field(..., description="Whether model supports tool calling")
    supports_vision: bool = Field(..., description="Whether model supports vision")
    supports_streaming: bool = Field(..., description="Whether model supports streaming")
    input_price_per_1m: float = Field(..., description="Input price per 1M tokens")
    output_price_per_1m: float = Field(..., description="Output price per 1M tokens")


class ProviderModelsInfo(BaseModel):
    """Pydantic model for provider models information."""

    provider: LLMProvider = Field(..., description="Provider")
    models: list[ModelInfo] = Field(..., description="Available models for the provider")
    total_models: int = Field(..., description="Total number of models")
    default_model: str | None = Field(default=None, description="Default model for the provider")

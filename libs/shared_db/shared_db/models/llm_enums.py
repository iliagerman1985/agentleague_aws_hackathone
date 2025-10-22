"""LLM-related enums for the shared database."""

from enum import StrEnum

from pydantic import BaseModel

from common.enums import LLMProvider


class ModelMetadata(BaseModel):
    """Metadata for a specific LLM model."""

    display_name: str
    description: str
    context_window: int
    supports_tools: bool
    supports_vision: bool
    input_price_per_1m: float
    output_price_per_1m: float


class OpenAIModel(StrEnum):
    """Available OpenAI models."""

    FAST = "gpt-5-mini"  # Fast
    SLOW = "gpt-5"  # Slow


class AnthropicModel(StrEnum):
    """Available Anthropic models."""

    FAST = "anthropic.claude-haiku-4-5-20251001-v1:0"  # Fast
    SLOW = "anthropic.claude-sonnet-4-5-20250929-v1:0"  # Slow


class GoogleModel(StrEnum):
    """Available Google models."""

    FAST = "gemini-2.5-flash"  # Fast
    SLOW = "gemini-2.5-pro"  # Slow


class AWSBedrockModel(StrEnum):
    """Available AWS Bedrock models (using the same Anthropic models)."""

    FAST = "us.anthropic.claude-haiku-4-5-20251001-v1:0"  # Fast
    SLOW = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"  # Slow


# NOTE: Provider/model functions have been consolidated into ModelConfigFactory
# Use the following methods instead:
# - ModelConfigFactory.get_provider_models(provider) -> list[str]
# - ModelConfigFactory.validate_provider_model(provider, model) -> bool
# - ModelConfigFactory.get_default_model_for_provider(provider) -> str | None
# - ModelConfigFactory.get_configs_for_provider(provider) -> list[ModelConfig]


# Union type for all supported models
LLMModelType = OpenAIModel | AnthropicModel | GoogleModel | AWSBedrockModel


def get_default_model_for_provider(provider: LLMProvider) -> LLMModelType:
    """Get the default (fast) model for a given provider.

    This is the single source of truth for default model selection.
    Matches client/tests/constants/models.ts DEFAULT_MODELS.

    Args:
        provider: LLM provider enum

    Returns:
        The default fast model for the provider

    Raises:
        ValueError: If provider is not supported
    """

    default_models: dict[LLMProvider, LLMModelType] = {
        LLMProvider.OPENAI: OpenAIModel.FAST,
        LLMProvider.ANTHROPIC: AnthropicModel.FAST,
        LLMProvider.GOOGLE: GoogleModel.FAST,
        LLMProvider.AWS_BEDROCK: AWSBedrockModel.FAST,
    }

    if provider not in default_models:
        raise ValueError(f"Unsupported provider: {provider}")

    return default_models[provider]


class LLMUsageScenario(StrEnum):
    """Scenarios where LLM usage is tracked."""

    AGENT_MOVE = "agent_move"
    TOOL_GENERATION = "tool_generation"
    TEST_GENERATION = "test_generation"
    STATE_GENERATION = "state_generation"
    AGENT_INSTRUCTIONS_GENERATION = "agent_instructions_generation"

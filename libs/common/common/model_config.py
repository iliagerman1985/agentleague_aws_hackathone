"""Model configuration factory for LLM providers."""

from dataclasses import dataclass
from typing import Any

from common.enums import LLMProvider
from shared_db.models.llm_enums import AnthropicModel, AWSBedrockModel, GoogleModel, OpenAIModel


@dataclass
class ModelConfig:
    """Configuration for a specific model."""

    provider: LLMProvider
    model_id: str
    display_name: str
    max_tokens_param: str  # "max_tokens" or "max_completion_tokens"
    supported_temperature_range: tuple[float, float]  # (min, max)
    default_temperature: float
    supports_streaming: bool = True
    supports_tools: bool = True
    supports_vision: bool = False
    context_window: int = 128000
    input_price_per_1m: float = 0.0
    output_price_per_1m: float = 0.0


class ModelConfigFactory:
    """Factory for model configurations."""

    _configs: dict[str, ModelConfig] = {
        # OpenAI Models
        OpenAIModel.SLOW: ModelConfig(
            provider=LLMProvider.OPENAI,
            model_id=OpenAIModel.SLOW,
            display_name="GPT-5",
            max_tokens_param="max_completion_tokens",
            supported_temperature_range=(1.0, 1.0),  # Only supports temperature=1
            default_temperature=1.0,
            supports_streaming=True,
            supports_tools=True,
            supports_vision=True,
            context_window=200000,
            input_price_per_1m=10.0,
            output_price_per_1m=30.0,
        ),
        OpenAIModel.FAST: ModelConfig(
            provider=LLMProvider.OPENAI,
            model_id=OpenAIModel.FAST,
            display_name="GPT-5 Mini",
            max_tokens_param="max_completion_tokens",
            supported_temperature_range=(1.0, 1.0),  # Only supports temperature=1
            default_temperature=1.0,
            supports_streaming=True,
            supports_tools=True,
            supports_vision=True,
            context_window=200000,
            input_price_per_1m=1.0,
            output_price_per_1m=4.0,
        ),
        # Anthropic Models
        AnthropicModel.SLOW: ModelConfig(
            provider=LLMProvider.ANTHROPIC,
            model_id=AnthropicModel.SLOW,
            display_name="Claude Sonnet 4",
            max_tokens_param="max_tokens",
            supported_temperature_range=(0.0, 1.0),
            default_temperature=0.7,
            supports_streaming=True,
            supports_tools=True,
            supports_vision=True,
            context_window=500000,
            input_price_per_1m=20.0,
            output_price_per_1m=100.0,
        ),
        AnthropicModel.FAST: ModelConfig(
            provider=LLMProvider.ANTHROPIC,
            model_id=AnthropicModel.FAST,
            display_name="Claude Haiku 3.5",
            max_tokens_param="max_tokens",
            supported_temperature_range=(0.0, 1.0),
            default_temperature=0.7,
            supports_streaming=True,
            supports_tools=True,
            supports_vision=True,
            context_window=500000,
            input_price_per_1m=5.0,
            output_price_per_1m=25.0,
        ),
        # Google Models
        GoogleModel.SLOW: ModelConfig(
            provider=LLMProvider.GOOGLE,
            model_id=GoogleModel.SLOW,
            display_name="Gemini 2.5 Pro",
            max_tokens_param="max_tokens",
            supported_temperature_range=(0.0, 2.0),
            default_temperature=0.7,
            supports_streaming=True,
            supports_tools=True,
            supports_vision=True,
            context_window=2000000,
            input_price_per_1m=2.0,
            output_price_per_1m=8.0,
        ),
        GoogleModel.FAST: ModelConfig(
            provider=LLMProvider.GOOGLE,
            model_id=GoogleModel.FAST,
            display_name="Gemini 2.5 Flash",
            max_tokens_param="max_tokens",
            supported_temperature_range=(0.0, 2.0),
            default_temperature=0.7,
            supports_streaming=True,
            supports_tools=True,
            supports_vision=True,
            context_window=1000000,
            input_price_per_1m=0.2,
            output_price_per_1m=0.8,
        ),
        # AWS Bedrock Models
        AWSBedrockModel.FAST: ModelConfig(
            provider=LLMProvider.AWS_BEDROCK,
            model_id=AWSBedrockModel.FAST,
            display_name="AWS Claude Haiku 3.5",
            max_tokens_param="max_tokens",
            supported_temperature_range=(0.0, 1.0),
            default_temperature=0.7,
            supports_streaming=True,
            supports_tools=True,
            supports_vision=True,
            context_window=500000,
            input_price_per_1m=5.0,
            output_price_per_1m=25.0,
        ),
        AWSBedrockModel.SLOW: ModelConfig(
            provider=LLMProvider.AWS_BEDROCK,
            model_id=AWSBedrockModel.SLOW,
            display_name="AWS Claude Sonnet 4",
            max_tokens_param="max_tokens",
            supported_temperature_range=(0.0, 1.0),
            default_temperature=0.7,
            supports_streaming=True,
            supports_tools=True,
            supports_vision=True,
            context_window=500000,
            input_price_per_1m=20.0,
            output_price_per_1m=100.0,
        ),
    }

    @classmethod
    def get_config(cls, model_id: str) -> ModelConfig | None:
        """Get configuration for a model."""
        return cls._configs.get(model_id)

    @classmethod
    def get_configs_for_provider(cls, provider: LLMProvider) -> list[ModelConfig]:
        """Get all configurations for a provider."""
        return [config for config in cls._configs.values() if config.provider == provider]

    @classmethod
    def is_model_supported(cls, model_id: str) -> bool:
        """Check if a model is supported."""
        return model_id in cls._configs

    @classmethod
    def get_max_tokens_param(cls, model_id: str) -> str:
        """Get the correct max tokens parameter name for a model."""
        config = cls.get_config(model_id)
        return config.max_tokens_param if config else "max_tokens"

    @classmethod
    def get_safe_temperature(cls, model_id: str, requested_temperature: float) -> float:
        """Get a safe temperature value for a model."""
        config = cls.get_config(model_id)
        if not config:
            return requested_temperature

        min_temp, max_temp = config.supported_temperature_range
        if min_temp == max_temp:
            # Model only supports one temperature value
            return min_temp

        # Clamp to supported range
        return max(min_temp, min(max_temp, requested_temperature))

    @classmethod
    def build_api_params(cls, model_id: str, base_params: dict[str, Any]) -> dict[str, Any]:
        """Build API parameters with model-specific adjustments."""
        config = cls.get_config(model_id)
        if not config:
            return base_params

        params = base_params.copy()

        # Handle max_tokens parameter
        if "max_tokens" in params:
            max_tokens_value = params.pop("max_tokens")
            params[config.max_tokens_param] = max_tokens_value

        # Handle temperature parameter
        if "temperature" in params:
            params["temperature"] = cls.get_safe_temperature(model_id, params["temperature"])

        return params

    @classmethod
    def get_provider_models(cls, provider: LLMProvider) -> list[str]:
        """Get list of model IDs for a specific provider.

        Args:
            provider: LLM provider enum

        Returns:
            List of model ID strings for the provider
        """
        return [config.model_id for config in cls.get_configs_for_provider(provider)]

    @classmethod
    def validate_provider_model(cls, provider: LLMProvider, model: str) -> bool:
        """Validate that a model is available for the given provider.

        Args:
            provider: LLM provider enum
            model: Model identifier string

        Returns:
            True if model is valid for the provider
        """
        return model in cls.get_provider_models(provider)

    @classmethod
    def get_default_model_for_provider(cls, provider: LLMProvider) -> str | None:
        """Get the default (fastest) model for a provider.

        Args:
            provider: LLM provider enum

        Returns:
            Default model ID for the provider, or None if no models available
        """
        configs = cls.get_configs_for_provider(provider)
        if not configs:
            return None

        # Return the first model as default (they're typically ordered fastest first)
        return configs[0].model_id

    @classmethod
    def get_all_providers(cls) -> list[LLMProvider]:
        """Get list of all supported providers.

        Returns:
            List of LLM provider enums
        """
        providers: set[LLMProvider] = set()
        for config in cls._configs.values():
            providers.add(config.provider)
        return list(providers)

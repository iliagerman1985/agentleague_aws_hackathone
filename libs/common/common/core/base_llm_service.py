"""Base LLM service interface and factory pattern."""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any

from common.core.litellm_schemas import (
    ChatMessage,
    LiteLLMConfig,
    LiteLLMResponse,
)
from common.enums import LLMProvider
from common.exceptions import (
    ProviderNotAvailableError,
    ServiceRegistrationError,
    UnsupportedProviderError,
)
from common.models import (
    ProviderErrorInfo,
    ProviderInfo,
    ServiceFactoryInfo,
)
from common.utils.utils import get_logger

logger = get_logger(__name__)


# Configuration service interface is handled through duck typing
# Any object with a get_provider_config method will work


class BaseLLMService(ABC):
    """Abstract base class for LLM services."""

    @abstractmethod
    async def chat_completion(
        self, provider: LLMProvider, model: str, messages: list[ChatMessage], api_key: str, config: LiteLLMConfig | None = None
    ) -> LiteLLMResponse:
        """Generate a chat completion."""

    @abstractmethod
    async def stream_chat_completion(
        self, provider: LLMProvider, model: str, messages: list[ChatMessage], api_key: str, config: LiteLLMConfig | None = None
    ) -> AsyncGenerator[str]:
        """Generate a streaming chat completion."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the service is available."""


class ProviderLLMService(ABC):
    """Abstract base class for provider-specific LLM services."""

    @property
    @abstractmethod
    def provider(self) -> LLMProvider:
        """Get the provider this service handles."""

    @abstractmethod
    async def chat_completion(self, model: str, messages: list[ChatMessage], api_key: str, config: LiteLLMConfig | None = None) -> LiteLLMResponse:
        """Generate a chat completion for this provider."""

    @abstractmethod
    async def stream_chat_completion(self, model: str, messages: list[ChatMessage], api_key: str, config: LiteLLMConfig | None = None) -> AsyncGenerator[str]:
        """Generate a streaming chat completion for this provider."""

    @abstractmethod
    async def test_api_key(self, model: str, api_key: str, test_prompt: str = "Hello, world!") -> str:
        """Test an API key with a simple prompt."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider service is available."""

    @abstractmethod
    def get_supported_models(self) -> list[str]:
        """Get list of supported models for this provider."""


class LLMServiceFactory:
    """Type-safe factory for creating and managing LLM services."""

    def __init__(self, config_service: Any = None):
        """Initialize the service factory.

        Args:
            config_service: Optional configuration service for provider configs
        """
        self._provider_services: dict[LLMProvider, ProviderLLMService] = {}
        self._base_service: BaseLLMService | None = None
        self._config_service = config_service

    def register_provider_service(self, service: ProviderLLMService) -> None:
        """Register a provider-specific service.

        Args:
            service: Provider service to register

        Raises:
            ServiceRegistrationError: If registration fails
        """
        try:
            provider = service.provider
            logger.info(f"Registering service for provider: {provider.value}")
            self._provider_services[provider] = service
        except Exception as e:
            raise ServiceRegistrationError(service.provider, str(e))

    def set_base_service(self, service: BaseLLMService) -> None:
        """Set the base LLM service (e.g., LiteLLM).

        Args:
            service: Base service to set
        """
        logger.info("Setting base LLM service")
        self._base_service = service

    def create_service(self, provider: LLMProvider) -> ProviderLLMService:
        """Create service instance for provider.

        Args:
            provider: Provider enum (NOT string)

        Returns:
            Service instance

        Raises:
            UnsupportedProviderError: If provider not supported
            ProviderNotAvailableError: If provider not available
        """
        # Validate provider is supported
        if provider not in self._provider_services:
            supported = list(self._provider_services.keys())
            raise UnsupportedProviderError(provider, supported)

        service = self._provider_services[provider]

        # Check if service is available
        if not service.is_available():
            raise ProviderNotAvailableError(provider, "Service not available")

        return service

    def get_provider_service(self, provider: LLMProvider) -> ProviderLLMService | None:
        """Get a provider-specific service.

        Args:
            provider: Provider enum (NOT string)

        Returns:
            Provider service or None if not found
        """
        return self._provider_services.get(provider)

    def get_base_service(self) -> BaseLLMService | None:
        """Get the base LLM service."""
        return self._base_service

    def get_available_providers(self) -> list[LLMProvider]:
        """Get list of available providers.

        Returns:
            List of available provider enums
        """
        available: list[LLMProvider] = []
        for provider, service in self._provider_services.items():
            if service.is_available():
                available.append(provider)
        return available

    def is_provider_available(self, provider: LLMProvider) -> bool:
        """Check if a specific provider is available.

        Args:
            provider: Provider enum (NOT string)

        Returns:
            True if provider is available
        """
        service = self._provider_services.get(provider)
        return service is not None and service.is_available()

    def is_provider_configured(self, provider: LLMProvider) -> bool:
        """Check if provider is properly configured.

        Args:
            provider: Provider enum (NOT string)

        Returns:
            True if provider is configured
        """
        if not self._config_service:
            return False

        try:
            config = self._config_service.get_provider_config(provider.value)
            return config is not None
        except Exception:
            return False

    def get_provider_info(self, provider: LLMProvider) -> ProviderInfo:
        """Get information about a provider.

        Args:
            provider: Provider enum (NOT string)

        Returns:
            Provider information with Pydantic validation

        Raises:
            UnsupportedProviderError: If provider not supported
        """
        if provider not in self._provider_services:
            supported = list(self._provider_services.keys())
            raise UnsupportedProviderError(provider, supported)

        service = self._provider_services[provider]
        is_configured = self.is_provider_configured(provider)
        is_available = service.is_available()

        config_data = None
        if is_configured and self._config_service:
            try:
                config = self._config_service.get_provider_config(provider.value)
                if config:
                    # Config is already a ProviderConfigData from the protocol
                    config_data = config
            except Exception as e:
                logger.warning(f"Failed to load config for {provider.value}: {e}")

        return ProviderInfo(
            name=provider.value,
            service_class=service.__class__.__name__,
            is_supported=True,
            is_configured=is_configured,
            is_available=is_available,
            config=config_data,
            supported_models=service.get_supported_models(),
        )

    def get_all_providers_info(self) -> dict[LLMProvider, ProviderInfo | ProviderErrorInfo]:
        """Get information about all providers.

        Returns:
            Dictionary with ENUM keys (not strings) and Pydantic model values
        """
        providers_info: dict[LLMProvider, ProviderInfo | ProviderErrorInfo] = {}

        for provider in self._provider_services.keys():
            try:
                providers_info[provider] = self.get_provider_info(provider)
            except Exception as e:
                providers_info[provider] = ProviderErrorInfo(error=str(e), error_type=type(e).__name__)

        return providers_info

    def get_factory_info(self) -> ServiceFactoryInfo:
        """Get information about the service factory.

        Returns:
            Service factory information with Pydantic validation
        """
        total_providers = len(self._provider_services)
        available_providers = len(self.get_available_providers())
        configured_providers = sum(1 for provider in self._provider_services.keys() if self.is_provider_configured(provider))

        return ServiceFactoryInfo(
            total_providers=total_providers,
            available_providers=available_providers,
            configured_providers=configured_providers,
            base_service_available=self._base_service is not None and self._base_service.is_available(),
        )


# Global factory instance
_llm_factory: LLMServiceFactory | None = None


def get_llm_factory() -> LLMServiceFactory:
    """Get the global LLM factory instance."""
    global _llm_factory
    if _llm_factory is None:
        _llm_factory = LLMServiceFactory()
    return _llm_factory

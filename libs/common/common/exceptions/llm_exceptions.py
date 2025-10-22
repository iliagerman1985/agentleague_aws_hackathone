"""Custom exceptions for LLM service operations."""

from common.enums import LLMProvider


class LLMServiceError(Exception):
    """Base exception for LLM service errors."""


class UnsupportedProviderError(LLMServiceError):
    """Raised when an unsupported LLM provider is requested."""

    def __init__(self, provider: LLMProvider, supported_providers: list[LLMProvider] | None = None):
        self.provider = provider
        self.supported_providers = supported_providers or []

        if self.supported_providers:
            supported_list = ", ".join([p.value for p in self.supported_providers])
            message = f"Unsupported provider: {provider.value}. Supported providers: {supported_list}"
        else:
            message = f"Unsupported provider: {provider.value}"

        super().__init__(message)


class ProviderConfigurationError(LLMServiceError):
    """Raised when provider configuration is invalid or missing."""

    def __init__(self, provider: LLMProvider, message: str):
        self.provider = provider
        super().__init__(f"Configuration error for {provider.value}: {message}")


class ProviderNotAvailableError(LLMServiceError):
    """Raised when a provider service is not available."""

    def __init__(self, provider: LLMProvider, reason: str | None = None):
        self.provider = provider
        self.reason = reason

        if reason:
            message = f"Provider {provider.value} is not available: {reason}"
        else:
            message = f"Provider {provider.value} is not available"

        super().__init__(message)


class ModelValidationError(LLMServiceError):
    """Raised when a model is not valid for a provider."""

    def __init__(self, provider: LLMProvider, model: str, valid_models: list[str] | None = None):
        self.provider = provider
        self.model = model
        self.valid_models = valid_models or []

        if self.valid_models:
            valid_list = ", ".join(self.valid_models)
            message = f"Model '{model}' is not valid for provider {provider.value}. Valid models: {valid_list}"
        else:
            message = f"Model '{model}' is not valid for provider {provider.value}"

        super().__init__(message)


class APIKeyTestError(LLMServiceError):
    """Raised when API key testing fails."""

    def __init__(self, provider: LLMProvider, reason: str):
        self.provider = provider
        self.reason = reason
        super().__init__(f"API key test failed for {provider.value}: {reason}")


class LLMRequestError(LLMServiceError):
    """Raised when an LLM request fails."""

    def __init__(self, provider: LLMProvider, model: str, reason: str):
        self.provider = provider
        self.model = model
        self.reason = reason
        super().__init__(f"LLM request failed for {provider.value}/{model}: {reason}")


class ServiceFactoryError(LLMServiceError):
    """Raised when service factory operations fail."""


class ServiceRegistrationError(ServiceFactoryError):
    """Raised when service registration fails."""

    def __init__(self, provider: LLMProvider, reason: str):
        self.provider = provider
        self.reason = reason
        super().__init__(f"Failed to register service for {provider.value}: {reason}")

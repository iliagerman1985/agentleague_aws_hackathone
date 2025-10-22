"""Custom exceptions for the common library."""

from .llm_exceptions import (
    APIKeyTestError,
    LLMRequestError,
    LLMServiceError,
    ModelValidationError,
    ProviderConfigurationError,
    ProviderNotAvailableError,
    ServiceFactoryError,
    ServiceRegistrationError,
    UnsupportedProviderError,
)

__all__ = [
    "APIKeyTestError",
    "LLMRequestError",
    "LLMServiceError",
    "ModelValidationError",
    "ProviderConfigurationError",
    "ProviderNotAvailableError",
    "ServiceFactoryError",
    "ServiceRegistrationError",
    "UnsupportedProviderError",
]

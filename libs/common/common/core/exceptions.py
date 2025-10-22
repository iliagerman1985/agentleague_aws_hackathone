"""Custom exceptions for the application."""

from typing import Any


class AppException(Exception):
    """Base exception class for application-specific errors."""

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(AppException):
    """Raised when authentication fails."""


class AuthorizationError(AppException):
    """Raised when authorization fails."""


class ValidationError(AppException):
    """Raised when input validation fails."""


class CognitoError(AppException):
    """Raised when Cognito operations fail."""


class UserNotFoundError(AppException):
    """Raised when a user is not found."""


class UserAlreadyExistsError(AppException):
    """Raised when trying to create a user that already exists."""


# Cognito-specific error mappings
COGNITO_ERROR_MESSAGES = {
    "UserNotFoundException": "User not found. Please check your email address.",
    "NotAuthorizedException": "Invalid email or password. Please try again.",
    "UserNotConfirmedException": "Please confirm your email address before signing in.",
    "PasswordResetRequiredException": "Password reset is required. Please reset your password.",
    "UserLambdaValidationException": "User validation failed. Please contact support.",
    "InvalidPasswordException": "Password does not meet requirements. Please choose a stronger password.",
    "InvalidParameterException": "Invalid request parameters. Please check your input.",
    "TooManyRequestsException": "Too many requests. Please wait a moment and try again.",
    "LimitExceededException": "Request limit exceeded. Please try again later.",
    "ExpiredCodeException": "The confirmation code has expired. Please request a new code.",
    "CodeMismatchException": "Invalid confirmation code. Please check the code and try again.",
    "AliasExistsException": "An account with this email already exists.",
    "UsernameExistsException": "An account with this email already exists.",
    "InvalidLambdaResponseException": "Service error. Please try again later.",
    "UnexpectedLambdaException": "Service error. Please try again later.",
    "UserPoolTaggingException": "Service configuration error. Please contact support.",
    "InternalErrorException": "Internal service error. Please try again later.",
}


def get_user_friendly_error_message(
    cognito_error_code: str,
    default_message: str | None = None,
) -> str:
    """Get a user-friendly error message for a Cognito error code.

    Args:
        cognito_error_code: The Cognito error code
        default_message: Default message if no mapping found

    Returns:
        User-friendly error message
    """
    return COGNITO_ERROR_MESSAGES.get(
        cognito_error_code,
        default_message or "An unexpected error occurred. Please try again.",
    )

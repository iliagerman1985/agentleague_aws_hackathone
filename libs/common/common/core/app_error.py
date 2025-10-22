from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from common.utils.json_model import JsonModel


class ErrorDetails(JsonModel):
    scope: str
    code: str
    message: str
    details: dict[str, Any] | None = None
    context: dict[str, Any] | None = None


class ErrorConfig(JsonModel):
    scope: str
    code: str
    default_message: str
    http_status: int | None = None
    retryable: bool = False
    send_notification: bool = True
    reporting_channel: str = "errors"

    def create(
        self,
        message: str | None = None,
        details: dict[str, Any] | None = None,
        http_status: int | None = None,
        cause: BaseException | None = None,
        retryable: bool | None = None,
        send_notification: bool | None = None,
        reporting_channel: str | None = None,
    ) -> AppException:
        msg = message if message is not None else self.default_message
        http = http_status if http_status is not None else self.http_status
        retry = self.retryable if retryable is None else retryable
        notify = self.send_notification if send_notification is None else send_notification
        channel = self.reporting_channel if reporting_channel is None else reporting_channel

        # If the cause is also an AppError, merge details
        if isinstance(cause, AppError):
            scope = cause.details.scope
            code = cause.details.code
            http = cause.http_status
            retry = cause.retryable
            notify = cause.send_notification
            channel = cause.reporting_channel
            ctx = cause.details.context
            if details and cause.details.details:
                details = {**cause.details.details, **details}
            elif cause.details.details:
                details = cause.details.details
            if cause.details.message:
                msg = f"{msg}: {cause.details.message}" if msg else cause.details.message
        else:
            scope = self.scope
            code = self.code
            ctx = None

        app_error = AppError(
            details=ErrorDetails(scope=scope, code=code, message=msg, details=details, context=ctx),
            http_status=http,
            cause=cause,
            retryable=retry,
            send_notification=notify,
            reporting_channel=channel,
        )
        return AppException(app_error)

    def is_(self, error: BaseException) -> bool:
        return AppException.is_(error, self)


class Errors:
    class Generic:
        INVALID_INPUT = ErrorConfig(scope="generic", code="invalid_input", default_message="Invalid input", http_status=400)
        ACCESS_DENIED = ErrorConfig(scope="generic", code="access_denied", default_message="Access denied", http_status=403)
        INTERNAL_ERROR = ErrorConfig(scope="generic", code="internal_error", default_message="Internal error", http_status=500)
        DECRYPTION_FAILED = ErrorConfig(scope="security", code="decryption_failed", default_message="Failed to decrypt data", http_status=500)
        UNKNOWN_ERROR = ErrorConfig(scope="generic", code="unknown_error", default_message="Unknown error", http_status=500)

    class Game:
        CONCURRENT_PROCESSING = ErrorConfig(
            scope="game", code="concurrent_processing", default_message="Concurrent processing", http_status=409, retryable=True
        )
        ALREADY_PROCESSING = ErrorConfig(scope="game", code="already_processing", default_message="Game is already being processed", http_status=409)
        NOT_FOUND = ErrorConfig(scope="game", code="not_found", default_message="Game not found", http_status=404)
        NOT_PLAYER_MOVE = ErrorConfig(scope="game", code="not_player_move", default_message="Not player's move")
        ALREADY_FINISHED = ErrorConfig(scope="game", code="already_finished", default_message="Game already finished", http_status=409)
        ALREADY_IN_QUEUE = ErrorConfig(scope="game", code="already_in_queue", default_message="Agent already in matchmaking queue", http_status=409)
        PLAYER_NOT_IN_GAME = ErrorConfig(scope="game", code="player_not_in_game", default_message="Player not in game", http_status=404)
        TURN_ADVANCEMENT_CONFLICT = ErrorConfig(
            scope="game", code="turn_advancement_conflict", default_message="Turn advancement conflict", http_status=409, retryable=False
        )

    class Llm:
        NOT_FOUND = ErrorConfig(scope="llm", code="not_found", default_message="LLM not found", http_status=404)

    class Agent:
        NOT_FOUND = ErrorConfig(scope="agent", code="not_found", default_message="Agent not found", http_status=404)
        INVALID_OUTPUT = ErrorConfig(scope="agent", code="invalid_output", default_message="Invalid agent output")
        TOOL_CALL_FAILED = ErrorConfig(scope="agent", code="tool_call_failed", default_message="Tool call failed")
        TOOL_CALL_REQUIRED = ErrorConfig(
            scope="agent", code="tool_call_required", default_message="Agent requested tool call - frontend should handle execution"
        )
        MAX_ITERATIONS_EXCEEDED = ErrorConfig(scope="agent", code="max_iterations_exceeded", default_message="Max iterations exceeded")
        INVALID_ENVIRONMENT = ErrorConfig(
            scope="agent", code="invalid_environment", default_message="Agent environment does not match game type", http_status=400
        )


class AppError(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    details: ErrorDetails = Field(..., description="Error details")
    http_status: int | None = Field(default=None, description="HTTP status code")
    retryable: bool = Field(default=False, description="Whether the error is retryable")
    send_notification: bool = Field(default=True, description="Whether to send notification")
    reporting_channel: str = Field(default="app-error", description="Reporting channel")
    cause: BaseException | None = Field(default=None, description="Underlying cause")

    def __init__(
        self,
        details: ErrorDetails,
        http_status: int | None = None,
        cause: BaseException | None = None,
        retryable: bool = False,
        send_notification: bool = True,
        reporting_channel: str = "app-error",
        **data: Any,
    ) -> None:
        computed_retryable = retryable and (cause is None or should_retry_exception(cause))
        computed_send_notification = send_notification and (cause is None or should_send_exception_notification(cause))
        computed_reporting_channel = reporting_channel if cause is None or not isinstance(cause, AppError) else cause.reporting_channel

        super().__init__(
            details=details,
            http_status=http_status,
            retryable=computed_retryable,
            send_notification=computed_send_notification,
            reporting_channel=computed_reporting_channel,
            cause=cause,
            **data,
        )

    @staticmethod
    def is_(error: BaseException, error_config: ErrorConfig) -> bool:
        return isinstance(error, AppError) and error.details.scope == error_config.scope and error.details.code == error_config.code


# TODO: Make this consistent
class AppException(Exception):
    """Exception wrapper for AppError that can be raised."""

    def __init__(self, app_error: AppError) -> None:
        self.app_error = app_error
        super().__init__(app_error.details.message)

    @property
    def details(self) -> ErrorDetails:
        return self.app_error.details

    @property
    def http_status(self) -> int | None:
        return self.app_error.http_status

    @property
    def retryable(self) -> bool:
        return self.app_error.retryable

    @property
    def send_notification(self) -> bool:
        return self.app_error.send_notification

    @property
    def reporting_channel(self) -> str:
        return self.app_error.reporting_channel

    @property
    def cause(self) -> BaseException | None:
        return self.app_error.cause

    @staticmethod
    def is_any_of(error: BaseException, *errors: ErrorConfig) -> bool:
        if isinstance(error, AppException):
            return any(AppError.is_(error, e) for e in errors)
        return isinstance(error, AppError) and any(AppError.is_(error, e) for e in errors)

    @staticmethod
    def is_(error: BaseException, error_config: ErrorConfig) -> bool:
        if isinstance(error, AppException):
            return error.details.scope == error_config.scope and error.details.code == error_config.code
        return isinstance(error, AppError) and error.details.scope == error_config.scope and error.details.code == error_config.code

    @staticmethod
    def get_details(error: BaseException) -> ErrorDetails | None:
        if isinstance(error, AppException):
            return error.details
        return error.details if isinstance(error, AppError) else None


def should_retry_exception(exception: BaseException) -> bool:
    if isinstance(exception, AppException):
        return exception.retryable
    return not isinstance(exception, AppError) or exception.retryable


def should_send_exception_notification(exception: BaseException) -> bool:
    if isinstance(exception, AppException):
        return exception.send_notification
    return not isinstance(exception, AppError) or exception.send_notification

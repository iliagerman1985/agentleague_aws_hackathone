from __future__ import annotations

import asyncio
import os
import time
from collections.abc import Callable
from datetime import timedelta
from typing import TYPE_CHECKING, Any, override

from prometheus_client import Counter, Gauge, Histogram

from common.core.app_error import AppException, should_retry_exception, should_send_exception_notification
from common.core.aws_manager import AwsManager
from common.core.lifecycle import Lifecycle
from common.core.request_context import RequestContext
from common.ids import SqsMessageId
from common.utils import TSID, JsonModel, get_logger, human_readable_duration
from common.utils.msgspec import decode_json
from common.utils.utils import latency_buckets_2m

logger = get_logger()

if TYPE_CHECKING:
    from collections.abc import Awaitable

    from types_aiobotocore_sqs.type_defs import MessageTypeDef

_DEFAULT_VISIBILITY_TIMEOUT = timedelta(seconds=int(os.getenv("SQS_VISIBILITY_TIMEOUT", "60")))
_DEFAULT_WAIT_TIME = timedelta(seconds=20)
_DEFAULT_MAX_MESSAGES = 10

messages_polled = Histogram("messages_polled", "Amount of SQS messages polled in a single request", ["name"], buckets=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
messages_in_progress = Gauge("messages_in_progress", "Amount of SQS messages being handled at the moment", ["name"])
message_handling_latency = Histogram("message_handling_latency", "Time taken to handle SQS message", ["name"], buckets=latency_buckets_2m)
message_results = Counter("message_results", "Message handling results", ["name", "outcome", "error_type"])


class SqsClientConfig(JsonModel):
    name: str
    queue_url: str
    visibility_timeout: timedelta = _DEFAULT_VISIBILITY_TIMEOUT
    wait_time: timedelta = _DEFAULT_WAIT_TIME
    max_messages: int = _DEFAULT_MAX_MESSAGES


class SqsMessage[T](JsonModel):
    id: SqsMessageId
    request_context: RequestContext
    payload: T


class SqsClient[T](Lifecycle):
    _aws_manager: AwsManager
    _sqs_message_type: type[SqsMessage[T]]
    _config: SqsClientConfig[T]
    _poll_handler: Callable[[T, RequestContext], Awaitable[Any]] | None
    _poll_task: asyncio.Task[Any] | None
    _messages_polled: Histogram
    _messages_in_progress: Gauge
    _message_handling_latency: Histogram

    def __init__(
        self,
        aws_manager: AwsManager,
        sqs_message_type: type[SqsMessage[T]],
        config: SqsClientConfig[T],
        poll_handler: Callable[[T, RequestContext], Awaitable[Any]] | None = None,
    ) -> None:
        super().__init__()

        self._aws_manager = aws_manager
        self._sqs_message_type = sqs_message_type
        self._config = config
        self._poll_handler = poll_handler
        self._poll_task = None

        self._messages_polled = messages_polled.labels(name=config.name)
        self._messages_in_progress = messages_in_progress.labels(name=config.name)
        self._message_handling_latency = message_handling_latency.labels(name=config.name)

    def register_poll_handler(
        self,
        poll_handler: Callable[[T, RequestContext], Awaitable[Any]],
    ) -> None:
        """Register a poll handler for processing SQS messages.

        Can only be called before the client is started and only once.

        Args:
            poll_handler: The handler function to process messages

        Raises:
            RuntimeError: If the client is already running or already has a handler
        """
        if self._is_running:
            raise RuntimeError("Cannot register poll handler after client has started")
        if self._poll_handler is not None:
            raise RuntimeError("Poll handler already registered")

        self._poll_handler = poll_handler

    @override
    async def _start(self) -> None:
        if self._poll_handler:
            logger.info(f"{self._name_for_log} Starting polling task...")
            self._poll_task = asyncio.create_task(self._poll_loop(), name=f"sqs_poller_{self._name}")
            logger.info(f"{self._name_for_log} Starting polling task... Done.")

    @override
    async def _stop(self) -> None:
        if self._poll_task:
            logger.info(f"{self._name_for_log} Stopping polling task...")
            _ = self._poll_task.cancel("Stopping...")
            logger.info(f"{self._name_for_log} Stopping polling task... Done.")

    @property
    def _name(self) -> str:
        return self._config.name

    @property
    @override
    def _name_for_log(self) -> str:
        return f"SQS[{self._name}]"

    async def send(self, message: T, request_context: RequestContext | None = None, id: SqsMessageId | None = None) -> None:
        sqs_message = SqsMessage(
            id=id or SqsMessageId(TSID.create()),
            request_context=request_context or RequestContext.get(),
            payload=message,
        )
        _ = await self._aws_manager.sqs_client.send_message(
            QueueUrl=self._config.queue_url,
            MessageBody=sqs_message.to_json(),
        )

        logger.debug(f"{self._name_for_log} Message sent", message=sqs_message)

    async def _poll_loop(self) -> None:
        assert self._poll_handler, "Internal error: _poll_loop called without _poll_handler"
        while self._is_running:
            try:
                await self.poll_and_handle(self._poll_handler)
            except Exception as e:
                logger.exception(f"{self._name_for_log} Error in poll loop!", exc_info=e)

    async def poll_and_handle(
        self,
        handler: Callable[[T, RequestContext], Awaitable[Any]],
        visibility_timeout: timedelta | None = None,
        wait_time: timedelta | None = None,
        max_messages: int | None = None,
        handle_all_available: bool = True,
    ) -> None:
        visibility_timeout = visibility_timeout or self._config.visibility_timeout
        wait_time = wait_time or self._config.wait_time
        max_messages = max_messages or self._config.max_messages
        while True:
            response = await self._aws_manager.sqs_client.receive_message(
                QueueUrl=self._config.queue_url,
                VisibilityTimeout=int(visibility_timeout.total_seconds()),
                WaitTimeSeconds=int(wait_time.total_seconds()),
                MaxNumberOfMessages=max_messages,
                AttributeNames=["All"],
                MessageAttributeNames=["All"],
            )
            if not self._is_running or "Messages" not in response:
                return

            messages = response["Messages"]
            self._messages_polled.observe(len(messages))
            (logger.info if len(messages) >= 1 else logger.debug)(
                f"{self._name_for_log} Polled {len(messages)} messages",
                message_count=len(messages),
            )

            if not messages:
                return
            elif len(messages) == 1:
                await self._handle(messages[0], handler)
            elif len(messages) > 1:
                _ = await asyncio.gather(*[self._handle(message, handler) for message in messages], return_exceptions=True)

            if not handle_all_available:
                return

    async def _handle(self, raw_message: MessageTypeDef, handler: Callable[[T, RequestContext], Awaitable[None]]) -> None:
        with self._messages_in_progress.track_inprogress(), RequestContext.context() as request_context:
            assert "Body" in raw_message

            request_context.trigger = f"sqs_{self._name}"

            start = time.perf_counter()
            error: Exception | None = None
            message: SqsMessage[T] | None = None
            try:
                # Instead of directly validating the model from json with .model_validate_json, first parse it into a python dict and then validate.
                # This may seem redundant, but pydantic has issues with type unions when directly validating from json, but not from a python dict.
                message = self._sqs_message_type.model_validate(decode_json(raw_message["Body"]))
                request_context.override_from(message.request_context)
                await handler(message.payload, request_context)
            except Exception as e:
                if should_send_exception_notification(e):
                    # channel = e.reporting_channel if isinstance(e, AppError) else None
                    # await SlackNotifier.instance().send_error_message(error=e, channel=channel)
                    pass
                error = e

            elapsed: float
            if not error or not should_retry_exception(error):
                try:
                    assert "ReceiptHandle" in raw_message
                    delete_result = await self._aws_manager.sqs_client.delete_message(
                        QueueUrl=self._config.queue_url,
                        ReceiptHandle=raw_message["ReceiptHandle"],
                    )
                    logger.debug(f"{self._name_for_log} Message deleted.", result=delete_result)
                except Exception as e:
                    message_results.labels(name=self._name, outcome="delete_error", error_type=type(e).__name__).inc()
                    logger.exception(f"{self._name_for_log} Error deleting SQS message!")
                elapsed = time.perf_counter() - start
                if not error:
                    logger.info(f"{self._name_for_log} Done: {human_readable_duration(elapsed)}", elapsed=elapsed)
                    message_results.labels(name=self._name, outcome="success", error_type="").inc()
                else:
                    message_results.labels(name=self._name, outcome="error_non_retryable", error_type=type(error).__name__).inc()
                    details = AppException.get_details(error)
                    error_message = f"error [{details.scope} - {details.code}]: {details.message}" if details else f"{error.__class__.__name__}: {error!s}"
                    human_readable_elapsed = human_readable_duration(elapsed)
                    logger.error(
                        f"{self._name_for_log} Non-retryable {error_message} [{human_readable_elapsed}]",
                        exc_info=error,
                        elapsed=human_readable_elapsed,
                        details=details,
                    )
            else:
                elapsed = time.perf_counter() - start
                message_results.labels(name=self._name, outcome="error_retryable", error_type=type(error).__name__).inc()
                details = AppException.get_details(error)
                error_message = f"error [{details.scope} - {details.code}]: {details.message}" if details else f"{error.__class__.__name__}: {error!s}"
                human_readable_elapsed = human_readable_duration(elapsed)
                logger.error(
                    f"{self._name_for_log} Retryable {error_message} [{human_readable_elapsed}]",
                    exc_info=error,
                    elapsed=human_readable_elapsed,
                    details=details,
                )

            self._message_handling_latency.observe(elapsed)

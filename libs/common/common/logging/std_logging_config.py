# cSpell:ignore growthbook

from __future__ import annotations

import atexit
import logging
import os
import re
import sys
import traceback
from ast import literal_eval
from collections.abc import Iterable
from contextvars import ContextVar
from enum import Enum
from json import loads as json_loads
from logging import Filter, Handler, LogRecord, StreamHandler
from logging.handlers import QueueHandler, QueueListener
from queue import Queue
from typing import Any, cast

import structlog
from pydantic import BaseModel
from structlog.typing import EventDict, Processor, WrappedLogger

from common.core.request_context import RequestContext
from common.utils import TSID, encode_json, is_dict

_EXCLUDED_KEYS = {"openai_secrets"}
_active_handler_name = "standard"

ANSI_RESET = "\033[0m"
ANSI_KEY = "\033[38;5;37m"
ANSI_STRING = "\033[38;5;214m"
ANSI_NUMBER = "\033[38;5;81m"
ANSI_BOOL = "\033[38;5;69m"
ANSI_ERROR = "\033[1;38;5;196m"

_KEY_PATTERN = re.compile(r'^(\s*)"([^"\\]+)"(: )', re.MULTILINE)
_STRING_PATTERN = re.compile(r'(:\s*)"((?:\\.|[^"\\])*)"')
_NUMBER_PATTERN = re.compile(r"(:\s*)(-?\d+(?:\.\d+)?)")
_BOOL_NULL_PATTERN = re.compile(r"(:\s*)(true|false|null)")


def _apply_base_error_coloring(text: str) -> str:
    """Wrap text in the error color while preserving nested ANSI resets."""

    # Ensure any embedded resets retain the red background until the outer reset
    colored_body = text.replace(ANSI_RESET, f"{ANSI_RESET}{ANSI_ERROR}")
    return f"{ANSI_ERROR}{colored_body}{ANSI_RESET}"


def _colorize_json(json_text: str, level: str | None) -> str:
    """Apply ANSI coloring to JSON keys and values for console readability."""

    colored = _KEY_PATTERN.sub(r"\1" + ANSI_KEY + r'"\2"' + ANSI_RESET + r"\3", json_text)
    colored = _STRING_PATTERN.sub(r"\1" + ANSI_STRING + r'"\2"' + ANSI_RESET, colored)
    colored = _NUMBER_PATTERN.sub(r"\1" + ANSI_NUMBER + r"\2" + ANSI_RESET, colored)
    colored = _BOOL_NULL_PATTERN.sub(r"\1" + ANSI_BOOL + r"\2" + ANSI_RESET, colored)

    if level in {"error", "critical"}:
        return _apply_base_error_coloring(colored)
    return colored


class ColorizedJSONRenderer(structlog.processors.JSONRenderer):
    """Render event dictionaries as colorized, multi-line JSON."""

    def __call__(self, _logger: WrappedLogger, _name: str, event_dict: EventDict) -> str:
        level = event_dict.get("level")
        json_text = super().__call__(_logger, _name, event_dict)
        if isinstance(json_text, bytes):
            json_text = json_text.decode("utf-8")
        level_str = str(level) if level is not None else None
        return _colorize_json(json_text, level_str)


class ColoredErrorHandler(logging.Handler):
    """Custom handler that prints logging errors in bright red to stderr."""

    def handleError(self, record: LogRecord) -> None:
        """Handle errors that occur during logging by printing them in red."""
        RED = "\033[91m"
        BOLD = "\033[1m"
        RESET = "\033[0m"

        try:
            # Get the exception info
            ei = sys.exc_info()
            if ei and ei[0]:
                # Format the error message
                error_msg = f"{BOLD}{RED}{'=' * 80}\n"
                error_msg += "LOGGING ERROR\n"
                error_msg += f"{'=' * 80}\n"
                error_msg += f"Logger: {record.name}\n"
                error_msg += f"Level: {record.levelname}\n"
                error_msg += f"Message: {record.msg}\n"
                error_msg += f"{'=' * 80}\n"
                error_msg += "".join(traceback.format_exception(*ei))
                error_msg += f"{'=' * 80}{RESET}\n"

                # Write to stderr
                _ = sys.stderr.write(error_msg)
                _ = sys.stderr.flush()
        except Exception:
            # If we can't even print the error, fall back to default behavior
            super().handleError(record)


def _should_use_json_logging() -> bool:
    """Use JSON logs outside local/dev, while allowing opt-in locally via flag."""

    app_env = os.getenv("APP_ENV", "local").lower()
    if app_env not in ("development", "local"):
        return True
    log_json_format_env = os.getenv("LOG_JSON_FORMAT")
    if log_json_format_env is None:
        return False
    return log_json_format_env.lower() in {"true", "1", "t", "yes"}


def _get_formatter_name() -> str:
    """Get the appropriate formatter name based on environment and flags."""
    app_env = os.getenv("APP_ENV", "local").lower()
    if app_env not in ("development", "local"):
        # Always compact JSON outside local/dev for log parsers
        return "json"
    if _should_use_json_logging():
        pretty_env = os.getenv("LOG_JSON_PRETTY", "")
        pretty = pretty_env.lower() in {"true", "1", "t", "yes"}
        return "json_pretty" if pretty else "json"
    return "plain"


class LoggingQueueListener(QueueListener):
    """Custom ``QueueListener`` which starts and stops the listening process."""

    def __init__(self, queue: Queue[LogRecord], *handlers: Handler, respect_handler_level: bool = False) -> None:
        super().__init__(queue, *handlers, respect_handler_level=respect_handler_level)
        self.start()
        _ = atexit.register(self.stop)


def _combine_log_fields(
    _logger: WrappedLogger,
    _name: str,
    event_dict: EventDict,
) -> EventDict:
    """Combine specific log fields into a single 'log_info' field."""
    fields_to_combine = ["filename", "func_name", "level", "lineno", "logger", "operation", "timestamp"]

    combined_fields = {}
    for field in fields_to_combine:
        if field in event_dict:
            combined_fields[field] = event_dict.pop(field)

    if combined_fields:
        # Create a formatted string with all the fields
        log_info_parts: list[str] = []
        for field in fields_to_combine:
            if field in combined_fields:
                log_info_parts.append(f"{field}={combined_fields[field]}")

        event_dict["log_info"] = " ".join(log_info_parts)

    return event_dict


def _process_values(
    _logger: WrappedLogger,
    _name: str,
    event_dict: EventDict,
) -> EventDict:
    """A structlog processor that replaces ContextVar instances with their values and serializes pydantic models."""

    request_context = RequestContext.get_or_none()
    if request_context is not None:
        event_dict["requestContext"] = request_context

    # Process each key-value pair in the event dictionary
    # We need to use a list of items to avoid modifying the dictionary during iteration
    for key, value in list(event_dict.items()):
        # Skip env which we just set
        if key not in ["env"]:
            _process_value(event_dict, key, value)

    # level_num removed as requested

    return event_dict


def _process_value(event_dict: EventDict, key: str, value: Any) -> None:
    """Process a single value and update the event_dict directly.

    Args:
        event_dict: The event dictionary to update
        key: The key associated with the value
        value: The value to process

    This function may modify event_dict in place by:
    - Replacing values with processed versions
    - Adding additional keys for special types like TSID
    - Recursively processing nested dictionaries
    - Removing keys if the value is None or in _EXCLUDED_KEYS
    - Detecting large integers (potential TSIDs) and transforming them into a dict
      with 'id' (stringified number) and 'str' (short string format) keys.
    """
    # Skip excluded keys and None values
    if key in _EXCLUDED_KEYS or value is None:
        # Remove the key if it exists
        event_dict.pop(key, None)
        return

    # First, transform the value based on its type
    processed_value = value

    if isinstance(value, ContextVar):
        processed_value = value.get(None)  # type: ignore
        if processed_value is None:
            event_dict.pop(key, None)
            return
    elif isinstance(value, BaseModel):
        processed_value = value.model_dump(exclude_none=True, by_alias=True, mode="json")
    elif isinstance(value, Enum):
        processed_value = value.value
    elif isinstance(value, str):
        t = value.strip()
        if t.startswith(("{", "[")):
            # Try JSON first
            try:
                processed_value = json_loads(t)
            except Exception:
                # Fall back to Python literal representations
                try:
                    obj = literal_eval(t)
                    if isinstance(obj, (dict, list)):
                        processed_value = obj
                except Exception:
                    processed_value = value
        else:
            processed_value = value

        # Improve readability for multiline error-focused strings
        if key in {"exc_info", "stack", "traceback", "exception", "detail", "error"}:
            cleaned_value = processed_value.strip() if isinstance(processed_value, str) else processed_value
            if isinstance(cleaned_value, str) and "\n" in cleaned_value:
                processed_value = [line.rstrip() for line in cleaned_value.splitlines() if line]
    elif isinstance(value, int) and value > 100000000000000000:
        try:
            tsid = TSID(value)
            processed_value = {
                "id": str(tsid.number),
                "str": tsid.to_string(),
            }
        except Exception:  # noqa: S110
            # Failed to parse TSID, oh well.
            pass

    # Handle dictionary values (either original or transformed)
    if is_dict(processed_value):
        for k, v in list(processed_value.items()):
            _process_value(processed_value, k, v)

    event_dict[key] = processed_value


def json_serializer(value: EventDict, **_: Any) -> str:
    return encode_json(value).decode("utf-8")


def logging_processors() -> list[Processor]:
    processors: list[Processor] = [
        # structlog.contextvars.merge_contextvars if not ENVIRONMENT.is_local() else lambda _l, _n, e: e,
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,  # Add the name of the logger to event dict.
        structlog.stdlib.add_log_level,  # Add log level to event dict.
        structlog.stdlib.ExtraAdder(),  # Add extra attributes of `logging.LogRecord` objects.
        structlog.processors.TimeStamper(fmt="iso"),  # Add a timestamp in ISO 8601 format.
        structlog.processors.StackInfoRenderer(),
        # If the "stack_info" key in the event dict is true, remove it and render the current stack trace in the "stack" key.
        structlog.processors.UnicodeDecoder(),  # If some value is in bytes, decode it to a Unicode str.
        structlog.processors.CallsiteParameterAdder(  # Add callsite parameters.
            {
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.FUNC_NAME,
                structlog.processors.CallsiteParameter.LINENO,
            },
        ),
        structlog.stdlib.PositionalArgumentsFormatter(),  # Perform %-style formatting.
        _combine_log_fields,  # Combine specific fields into single log_info field
        _process_values,
        # notify_error,
    ]

    # Use the same formatter selection logic as stdlib logging
    formatter_name = _get_formatter_name()

    if formatter_name == "json":
        processors.append(structlog.processors.dict_tracebacks)
        processors.append(structlog.processors.JSONRenderer(sort_keys=True, default=json_serializer, indent=None))
    elif formatter_name == "json_pretty":
        processors.append(structlog.processors.dict_tracebacks)
        processors.append(ColorizedJSONRenderer(sort_keys=True, indent=2, default=json_serializer))
    else:  # plain
        processors.append(_filter_console_fields)
        processors.append(_human_readable_renderer)

    return processors


# Custom filter to suppress specific log messages
class NoHealthMetricsFilter(Filter):
    def filter(self, record: LogRecord) -> bool:
        message = record.getMessage()
        return not ("GET /health" in message or "GET /metrics" in message)


def _safe_processor_wrapper(processor: Processor) -> Processor:
    """Wrap a processor to ensure it never returns None.

    Some processors might return None in edge cases, which breaks the chain.
    This wrapper ensures they always return a valid EventDict.
    """
    def wrapper(_logger: WrappedLogger, _name: str, event_dict: EventDict) -> EventDict:
        result = processor(_logger, _name, event_dict)
        # Processors can return various types (str, bytes, dict, etc.) according to structlog's ProcessorReturnValue
        # If processor returns non-dict type, return the original event_dict
        if not isinstance(result, dict):
            return event_dict
        return result

    return cast(Processor, wrapper)


def _ensure_event_dict(_logger: WrappedLogger, _name: str, event_dict: Any) -> EventDict:
    """Ensure event_dict is a dict, not a string.

    Some stdlib loggers pass pre-formatted strings as record.msg.
    This processor detects that and wraps the string in a proper event dict.

    This runs in the foreign_pre_chain, so event_dict is actually record.msg at this point,
    which can be any type (str, dict, None, etc.).
    """
    # Handle None case (shouldn't happen, but be defensive)
    if event_dict is None:
        return {"event": ""}

    # If event_dict is a string (which means record.msg was a string)
    if isinstance(event_dict, str):
        t = event_dict.strip()
        # Try to parse it as JSON if it looks like a dict
        if t.startswith("{"):
            try:
                parsed = json_loads(t)
                if isinstance(parsed, dict):
                    return cast(EventDict, parsed)
            except Exception:
                try:
                    literal_obj = literal_eval(t)
                    if isinstance(literal_obj, dict):
                        return cast(EventDict, literal_obj)
                except Exception:
                    pass
        # Fall back to wrapping the string in an event dict
        return {"event": event_dict}

    # If it's already a dict, return it as-is
    if isinstance(event_dict, dict):
        return cast(EventDict, event_dict)

    # For any other type, convert to string and wrap
    return {"event": str(event_dict)}


def _filter_console_fields(_logger: WrappedLogger, _name: str, event_dict: EventDict) -> EventDict:
    """Filter event_dict to only include essential fields for console output.

    This removes all the verbose metadata that clutters console logs.
    Keep only: timestamp, level, logger, event, and any custom fields.
    """
    # Remove verbose metadata fields
    verbose_fields = {
        "log_info",
        "filename",
        "func_name",
        "lineno",
        "pathname",
        "module",
        "process",
        "thread",
        "thread_name",
        "process_name",
        "stack_info",
        "color_message",
        "message",  # Duplicate of 'event'
    }

    # Remove verbose fields
    for field in verbose_fields:
        event_dict.pop(field, None)

    return event_dict


def _human_readable_renderer(_logger: WrappedLogger, _name: str, event_dict: EventDict) -> str:
    """Render logs in a human-readable format with colors.

    Format: HH:MM:SS [level] logger message key=value

    This is a renderer (not a processor), so it returns a string directly.
    """
    import sys
    from datetime import datetime

    # Check if we're in a terminal that supports colors
    use_colors = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

    # ANSI color codes
    if use_colors:
        reset = "\033[0m"
        gray = "\033[90m"
        green = "\033[92m"
        yellow = "\033[93m"
        red = "\033[91m"
        cyan = "\033[96m"
        bold = "\033[1m"
    else:
        reset = gray = green = yellow = red = cyan = bold = ""

    # Get level color
    level = event_dict.get("level", "info")
    level_str = str(level).upper()
    if level_str == "DEBUG":
        level_color = gray
    elif level_str == "INFO":
        level_color = green
    elif level_str == "WARNING":
        level_color = yellow
    elif level_str == "ERROR":
        level_color = red
    elif level_str == "CRITICAL":
        level_color = f"{bold}{red}"
    else:
        level_color = reset

    # Build the log message
    timestamp = event_dict.get("timestamp", "")
    logger_name = event_dict.get("logger", "")
    raw_event = event_dict.get("event", "")
    if isinstance(raw_event, dict):
        event = ", ".join(f"{key}={value}" for key, value in raw_event.items())
    else:
        event = str(raw_event)

    if event.startswith("{") and event.endswith("}"):
        try:
            literal_event = literal_eval(event)
            if isinstance(literal_event, dict):
                literal_event_dict = cast(dict[str, Any], literal_event)
                inner_event = literal_event_dict.get("event")
                if isinstance(inner_event, dict):
                    inner_event_dict = cast(dict[str, Any], inner_event)
                    event = ", ".join(f"{key}={value}" for key, value in inner_event_dict.items())
                elif inner_event is not None:
                    event = str(inner_event)
                extra_payload = {key: value for key, value in literal_event_dict.items() if key != "event"}
                for extra_key, extra_value in extra_payload.items():
                    if extra_key not in event_dict:
                        event_dict[extra_key] = extra_value
        except Exception:
            pass

    if event.startswith("event="):
        event = event.split("=", 1)[1].strip()
    elif event.startswith("event: "):
        event = event.split(": ", 1)[1].strip()

    if not event:
        exception_summary = event_dict.get("exception")
        if exception_summary:
            event = str(exception_summary)

    # Convert ISO timestamp to short format (HH:MM:SS)
    short_time = ""
    if timestamp:
        try:
            # Parse ISO format timestamp and extract time
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            short_time = dt.strftime("%H:%M:%S")
        except Exception:
            # Fallback to original timestamp if parsing fails
            short_time = timestamp

    # Format: HH:MM:SS [level] logger message key=value
    parts: list[str] = []

    # Add short timestamp (gray)
    if short_time:
        parts.append(f"{gray}{short_time}{reset}")

    # Add level (colored based on severity)
    if level_str:
        parts.append(f"{level_color}[{level_str:<5}]{reset}")

    # Add logger name (cyan) - shortened if too long
    if logger_name:
        # Shorten logger name if it's too long
        if len(logger_name) > 20:
            logger_display = logger_name[-20:]
        else:
            logger_display = logger_name
        parts.append(f"{cyan}{logger_display:<20}{reset}")

    # Add event message (white/default) - this is the main message
    if event:
        if level_str in {"ERROR", "CRITICAL"}:
            parts.append(f"{bold}{level_color}{event}{reset}")
        else:
            parts.append(event)

    # Add any extra fields as key=value pairs (in gray for less emphasis)
    formatted_traceback = event_dict.pop("_formatted_traceback", None)

    skip_fields = {"timestamp", "level", "logger", "event", "exception"}
    extra_parts: list[str] = []
    for key, value in event_dict.items():
        if key not in skip_fields:
            # Format the value
            if isinstance(value, dict):
                dict_value = cast(dict[str, Any], value)
                try:
                    value_str = encode_json(dict_value).decode("utf-8")
                except Exception:
                    value_str = str(dict_value)
            elif isinstance(value, (list, tuple)):
                sequence_value = cast(Iterable[Any], value)
                value_str = ", ".join(str(item) for item in sequence_value)
            else:
                value_str = str(value)
            extra_parts.append(f"{gray}{key}={value_str}{reset}")

    # Combine main parts with a space
    result = " ".join(parts)

    # Add extra fields on the same line if they exist
    if extra_parts:
        result += f" {gray}({', '.join(extra_parts)}){reset}"

    if level_str in {"ERROR", "CRITICAL"}:
        stack_lines: list[str] = []

        if isinstance(formatted_traceback, Iterable) and not isinstance(formatted_traceback, str):
            formatted_traceback_iter = cast(Iterable[Any], formatted_traceback)
            stack_lines.extend(str(line) for line in formatted_traceback_iter)

        if not stack_lines:
            traceback_keys = ("traceback", "stack")
            for key in traceback_keys:
                value = event_dict.get(key)
                if not value:
                    continue
                if isinstance(value, list | tuple):
                    stack_lines.extend(str(line) for line in cast(Iterable[Any], value))
                else:
                    stack_lines.extend(str(value).splitlines())

        if stack_lines:
            header = f"\n{bold}{level_color}Traceback (most recent call last):{reset}"
            formatted_stack = "\n".join(f"{level_color}{line}{reset}" for line in stack_lines)
            result = f"{result}{header}\n{formatted_stack}"

    # Return the formatted string directly (not an EventDict)
    return result


class SafeProcessorFormatter(structlog.stdlib.ProcessorFormatter):
    """ProcessorFormatter that ensures record.msg is always a dict before formatting.

    This prevents 'str' object has no attribute 'copy' errors when stdlib loggers
    pass strings as record.msg instead of dicts.
    """

    def format(self, record: LogRecord) -> str:
        """Format a log record, ensuring record.msg is a dict."""
        # Ensure record.msg is a dict before calling parent format
        if not isinstance(record.msg, dict):
            # Wrap string messages in a dict
            if isinstance(record.msg, str):
                record.msg = {"event": record.msg}
            else:
                record.msg = {"event": str(record.msg)}

        return super().format(record)


class StdLoggingConfig:
    foreign_pre_chain_processors: list[Processor] = [
        _ensure_event_dict,  # Must be first to handle stringified messages from stdlib loggers
        _safe_processor_wrapper(structlog.contextvars.merge_contextvars),
        _safe_processor_wrapper(structlog.stdlib.add_logger_name),  # Add the name of the logger to event dict.
        _safe_processor_wrapper(structlog.stdlib.add_log_level),  # Add log level to event dict.
        _safe_processor_wrapper(structlog.stdlib.ExtraAdder()),  # Add extra attributes of `logging.LogRecord` objects.
        _safe_processor_wrapper(structlog.stdlib.PositionalArgumentsFormatter()),  # Perform %-style formatting.
        _safe_processor_wrapper(structlog.processors.TimeStamper(fmt="iso")),  # Add a timestamp in ISO 8601 format.
        _safe_processor_wrapper(structlog.processors.StackInfoRenderer()),
        # If the "stack_info" key in the event dict is true, remove it and render the current stack trace in the "stack" key.
        _safe_processor_wrapper(structlog.processors.UnicodeDecoder()),  # If some value is in bytes, decode it to a Unicode str.
        # Don't add CallsiteParameterAdder or _combine_log_fields for cleaner console output
        # These add verbose metadata that clutters the logs
        _process_values,
        # notify_error,
    ]

    structlog_processors = [*foreign_pre_chain_processors, structlog.stdlib.ProcessorFormatter.wrap_for_formatter]

    # Print JSON when we run, e.g., in a Docker container.
    # Also print structured tracebacks.
    # Compact JSON output (single line per log entry) for log parsers
    json_renderer: list[Processor] = [
        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
        structlog.processors.dict_tracebacks,
        structlog.processors.JSONRenderer(
            sort_keys=True,
            default=json_serializer,
            indent=None,  # Ensure compact single-line JSON output
        ),
    ]

    # Pretty JSON renderer (multi-line) for local readability when explicitly enabled
    json_renderer_pretty: list[Processor] = [
        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
        structlog.processors.dict_tracebacks,
        ColorizedJSONRenderer(sort_keys=True, indent=2, default=json_serializer),
    ]

    # Pretty printing when we run in a terminal session.
    # Use our custom human-readable renderer with colors
    console_renderer: list[Processor] = [
        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
        _filter_console_fields,  # Filter out verbose metadata BEFORE rendering
        _human_readable_renderer,  # Custom renderer for human-readable output (returns string directly)
    ]

    formatters = {
        "json": {
            "()": SafeProcessorFormatter,
            "processors": json_renderer,  # For messages from structlog (includes final renderer)
            "foreign_pre_chain": foreign_pre_chain_processors,  # For messages from stdlib logging
        },
        "json_pretty": {
            "()": SafeProcessorFormatter,
            "processors": json_renderer_pretty,  # For messages from structlog (includes final renderer)
            "foreign_pre_chain": foreign_pre_chain_processors,  # For messages from stdlib logging
        },
        "plain": {
            "()": SafeProcessorFormatter,
            "processors": console_renderer,  # For messages from structlog (includes final renderer)
            "foreign_pre_chain": foreign_pre_chain_processors,  # For messages from stdlib logging
        },
        "key_value": {
            "()": SafeProcessorFormatter,
            "foreign_pre_chain": foreign_pre_chain_processors,  # For messages from stdlib logging
            "processor": structlog.processors.KeyValueRenderer(key_order=["timestamp", "level", "event", "logger"]),
        },
    }

    filters = {
        "no_health_metrics": {
            "()": NoHealthMetricsFilter,
        },
    }

    logger_factory = structlog.stdlib.LoggerFactory()

    # Declare handlers for type checkers; populated at module import time below.
    handlers: dict[str, Any] = {}


class ColoredStreamHandler(StreamHandler):  # type: ignore[type-arg]
    """StreamHandler that uses ColoredErrorHandler for error reporting."""

    def __init__(self, stream: Any = None) -> None:
        super().__init__(stream)  # type: ignore[call-arg]
        # Override the error handler
        self.handleError = ColoredErrorHandler().handleError


def _get_handlers() -> dict[str, Any]:
    """Get handlers with dynamic formatter selection based on environment."""
    formatter = _get_formatter_name()
    use_queue = formatter != "json_pretty"

    handlers: dict[str, Any] = {
        "console": {
            "class": ColoredStreamHandler,
            "level": "INFO",
            "stream": sys.stdout,
            "formatter": formatter,
            "filters": ["no_health_metrics"],
        }
    }

    active_handler = "console"

    if use_queue:
        handlers["standard"] = {
            "class": QueueHandler,
            "level": "INFO",
            "listener": LoggingQueueListener,
            "handlers": ["console"],
            "filters": ["no_health_metrics"],
        }
        handlers["queue_listener"] = {
            "class": QueueHandler,
            "level": "INFO",
            "listener": LoggingQueueListener,
            "handlers": ["console"],
            "filters": ["no_health_metrics"],
        }
        active_handler = "standard"
    else:
        # Provide a "standard" alias pointing directly to the console handler configuration
        handlers["standard"] = {
            "class": ColoredStreamHandler,
            "level": "INFO",
            "stream": sys.stdout,
            "formatter": formatter,
            "filters": ["no_health_metrics"],
        }
        active_handler = "standard"

    global _active_handler_name
    _active_handler_name = active_handler

    return handlers


# Initialize handlers at module level
StdLoggingConfig.handlers = _get_handlers()


common_logger_config = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": StdLoggingConfig.formatters,
    "handlers": StdLoggingConfig.handlers,
    "root": {
        "handlers": ["standard"],
        "level": "INFO",
    },
    "filters": StdLoggingConfig.filters,
    "loggers": {
        "botocore": {
            "handlers": ["standard"],
            "propagate": False,
            "level": "ERROR",
        },
        "aiobotocore": {
            "handlers": ["standard"],
            "propagate": False,
            "level": "ERROR",
        },
        "urllib3": {
            "handlers": ["standard"],
            "propagate": False,
            "level": "INFO",
        },
        "httpx": {
            "handlers": ["standard"],
            "propagate": False,
            "level": "ERROR",
        },
        "growthbook": {
            "handlers": ["standard"],
            "propagate": False,
            "level": "INFO",
        },
        "uvicorn": {
            "handlers": ["standard"],
            "level": "INFO",
            "propagate": False,
            "filters": ["no_health_metrics"],
        },
        "uvicorn.error": {
            "level": "INFO",
            "handlers": ["standard"],
            "propagate": False,
            "filters": ["no_health_metrics"],
        },
        "uvicorn.access": {
            "handlers": ["standard"],
            "level": "WARNING",
            "propagate": False,
            "filters": ["no_health_metrics"],
        },
    },
}


def _apply_active_handler() -> None:
    root_config = cast(dict[str, Any], common_logger_config["root"])
    root_config["handlers"] = [_active_handler_name]

    loggers_config = cast(dict[str, Any], common_logger_config["loggers"])
    for logger_cfg in loggers_config.values():
        if isinstance(logger_cfg, dict):
            logger_cfg["handlers"] = [_active_handler_name]


_apply_active_handler()

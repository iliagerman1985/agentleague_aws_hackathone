"""Centralized logging service for the application.
Provides structured JSON logging with configurable output destinations and log levels.
"""

import logging
import os
import sys
from enum import Enum
from logging import Handler, LogRecord
from pathlib import Path
from typing import Any, cast

from loguru import logger as loguru_logger
from pydantic import BaseModel

from common.core.config_service import ConfigService


class LogLevel(str, Enum):
    """Log levels supported by the logging service."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogConfig(BaseModel):
    """Configuration for the logging service."""

    level: LogLevel = LogLevel.INFO
    # Default to colorful human-readable logs
    json_format: bool = False
    json_pretty: bool = False
    console_output: bool = True
    file_output: bool = False
    log_file_path: str | None = None
    rotation: str = "20 MB"  # Size at which to rotate log files
    retention: str = "1 week"  # How long to keep log files
    compression: str = "zip"  # Compression format for rotated logs


class LoggingService:
    """Centralized logging service for the application.
    Provides structured JSON logging with configurable output destinations and log levels.
    """

    def __init__(self, config: LogConfig | None = None) -> None:
        """Initialize the logging service with the given configuration.
        If no configuration is provided, it will be loaded from the config service.
        """
        self.config = config or self._load_config_from_service()
        self._configure_loguru()

    def _using_structlog_bridge(self) -> bool:
        """Determine if loguru should forward logs into structlog.

        Non-local environments keep the legacy loguru JSON pipeline for compatibility.
        """

        app_env = os.getenv("APP_ENV", "local").lower()
        return app_env == "local"

    def _load_config_from_service(self) -> LogConfig:
        """Load logging configuration from the config service."""
        config_service = ConfigService()
        return LogConfig(
            level=LogLevel(config_service.get("log_level", "INFO").upper()),
            json_format=config_service.get("log_json_format", False),
            json_pretty=config_service.get("log_json_pretty", False),
            console_output=config_service.get("log_console_output", True),
            file_output=config_service.get("log_file_output", False),
            log_file_path=config_service.get("log_file_path"),
            rotation=config_service.get("log_rotation", "20 MB"),
            retention=config_service.get("log_retention", "1 week"),
            compression=config_service.get("log_compression", "zip"),
        )

    def _configure_loguru(self) -> None:
        """Configure loguru with the current settings."""
        # Remove default handlers
        loguru_logger.remove()

        # Decide whether to forward into structlog or use legacy loguru formatting
        use_structlog_bridge = self._using_structlog_bridge()

        if use_structlog_bridge:
            self._configure_structlog_bridge()
        else:
            self._configure_plain_loguru()

        # Add file handler if enabled
        if self.config.file_output and self.config.log_file_path:
            self._configure_file_sink()

    def _configure_structlog_bridge(self) -> None:
        """Forward loguru output into the stdlib/structlog pipeline."""

        if self.config.console_output:

            class StructlogForwardHandler(Handler):
                def emit(self, record: LogRecord) -> None:
                    logging.getLogger(record.name).handle(record)

            bridge = StructlogForwardHandler()
            bridge.setLevel(self.config.level.value)
            _ = loguru_logger.add(bridge, level=self.config.level.value, backtrace=True, diagnose=True)

    def _configure_plain_loguru(self) -> None:
        """Keep the existing loguru formatting for non-local environments."""

        serialize_flag = False

        if self.config.json_format and self.config.json_pretty:
            log_format: str | Any = self._pretty_json_formatter()
        elif self.config.json_format:
            log_format = "{message}"
            serialize_flag = True
        else:
            log_format = self._human_formatter()

        if self.config.console_output:
            _ = loguru_logger.add(
                sys.stdout,
                format=log_format,
                level=self.config.level.value,
                serialize=serialize_flag,
                backtrace=True,
                diagnose=True,
                colorize=not serialize_flag,
            )

    def _configure_file_sink(self) -> None:
        log_file_path = self.config.log_file_path or "logs/app.log"
        log_path = Path(log_file_path)
        if log_path.parent.exists() and not log_path.parent.is_dir():
            log_path.parent.unlink()
        log_path.parent.mkdir(parents=True, exist_ok=True)

        comp_raw = (self.config.compression or "").strip().lower()
        comp_map = {
            "gzip": "gz",
            "gz": "gz",
            "bzip2": "bz2",
            "bz2": "bz2",
            "xz": "xz",
            "zip": "zip",
            "tar.gz": "tar.gz",
            "tar": "tar",
        }
        comp_norm = comp_map.get(comp_raw, comp_raw)
        compression = None if comp_norm in {"none", "false", "0", ""} else comp_norm

        _ = loguru_logger.add(
            str(log_path),
            format="{message}",
            level=self.config.level.value,
            rotation=self.config.rotation,
            retention=self.config.retention,
            compression=compression,
            backtrace=True,
            diagnose=True,
        )

    def _pretty_json_formatter(self) -> Any:
        import re
        from ast import literal_eval
        from json import dumps, loads

        def _colorize_keys(text: str) -> str:
            CYAN = "\x1b[36m"
            RESET = "\x1b[0m"
            pattern = re.compile(r'(^\s*)"([^"\\]+)"(\s*: )', re.MULTILINE)
            return pattern.sub(lambda m: f'{m.group(1)}"{CYAN}{m.group(2)}{RESET}"{m.group(3)} ', text)

        def _coerce(v: Any) -> Any:
            if isinstance(v, str):
                t = v.strip()
                if t.startswith(("{", "[")):
                    try:
                        return loads(t)
                    except Exception:
                        try:
                            obj = literal_eval(t)
                            if isinstance(obj, (dict, list)):
                                return obj
                        except Exception:
                            pass
                return v
            if isinstance(v, dict):
                return {k: _coerce(x) for k, x in v.items()}
            if isinstance(v, list):
                return [_coerce(x) for x in v]
            return v

        def _formatter(record: dict[str, Any]) -> str:
            data = self._serialize_record(record)
            data = _coerce(data)
            s = dumps(data, ensure_ascii=False, indent=2)
            s = _colorize_keys(s)
            return s.replace("{", "{{").replace("}", "}}").replace("<", "\\<").replace(">", "\\>")

        return _formatter

    def _human_formatter(self) -> Any:
        from json import dumps

        def _escape_special_chars(text: str) -> str:
            return text.replace("{", "{{").replace("}", "}}").replace("<", "\\<").replace(">", "\\>")

        def _formatter(record: dict[str, Any]) -> str:
            time_str = record["time"].strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            level = record["level"].name
            name = record["name"]
            function = record["function"]
            line = record["line"]
            message = _escape_special_chars(record["message"])

            extras: dict[str, Any] = cast(dict[str, Any], record.get("extra") or {})
            extras_block = ""
            if extras:
                try:
                    extras_str: str = dumps(extras, ensure_ascii=False, indent=2, default=str)
                except Exception:
                    extras_str = str(extras)
                extras_block = f"\n<magenta>extra:</magenta> {_escape_special_chars(extras_str)}"

            return (
                f"<green>{time_str}</green> "
                f"| <level>{level: <8}</level> "
                f"| <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                f"<level>{message}</level>{extras_block}\n"
            )

        return _formatter

    def _serialize_record(self, record: Any) -> dict[str, object]:
        """Serialize a log record for JSON output.

        This is used by loguru's serialize parameter to convert the record to a dict
        that can be serialized to JSON.
        """
        # Basic log data
        serialized: dict[str, object] = {
            "timestamp": record["time"].strftime("%Y-%m-%d %H:%M:%S.%f"),
            "level": record["level"].name,
            "message": record["message"],
            "module": record["name"],
            "function": record["function"],
            "line": record["line"],
            "process_id": record["process"].id,
            "thread_id": record["thread"].id,
        }

        # Add exception info if available
        if record["exception"] is not None:
            serialized["exception"] = {
                "type": record["exception"].type,
                "value": str(record["exception"].value),
                "traceback": record["exception"].traceback,
            }

        # Add all extra fields at the top level
        if record["extra"]:
            for key, value in record["extra"].items():
                # Don't overwrite standard fields
                if key not in serialized:
                    serialized[key] = value

        return serialized

    def get_logger(self, name: str) -> "Logger":
        """Get a logger for the given name.

        Args:
            name: The name of the logger, typically the module name.

        Returns:
            A Logger instance configured with the current settings.
        """
        return Logger(name, self.config)

    def update_config(self, config: LogConfig) -> None:
        """Update the logging configuration.

        Args:
            config: The new configuration to apply.
        """
        self.config = config
        self._configure_loguru()


class Logger:
    """Logger class that wraps loguru logger with additional functionality."""

    def __init__(self, name: str, config: LogConfig) -> None:
        """Initialize a logger with the given name and configuration.

        Args:
            name: The name of the logger, typically the module name.
            config: The logging configuration to use.
        """
        self.name = name
        self.config = config
        # Do not bind `name` into extras to avoid clashing with Loguru's built-in {name}
        self.logger = loguru_logger

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log a debug message with all kwargs bound as extra fields."""
        self.logger.bind(**kwargs).opt(depth=1).debug(message)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log an info message with all kwargs bound as extra fields."""
        self.logger.bind(**kwargs).opt(depth=1).info(message)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log a warning message with all kwargs bound as extra fields."""
        self.logger.bind(**kwargs).opt(depth=1).warning(message)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log an error message with all kwargs bound as extra fields."""
        self.logger.bind(**kwargs).opt(depth=1).error(message)

    def critical(self, message: str, **kwargs: Any) -> None:
        """Log a critical message with all kwargs bound as extra fields."""
        self.logger.bind(**kwargs).opt(depth=1).critical(message)

    def exception(self, message: str, **kwargs: Any) -> None:
        """Log an exception message with traceback and all kwargs bound as extra fields."""
        self.logger.bind(**kwargs).opt(depth=1).exception(message)

    def log(self, level: str | int, message: str, **kwargs: Any) -> None:
        """Log a message with the specified level and all kwargs bound as extra fields."""
        self.logger.bind(**kwargs).opt(depth=1).log(level, message)

    def bind(self, **kwargs: Any) -> "Logger":
        """Bind contextual information to the logger.

        Args:
            **kwargs: Key-value pairs to bind to the logger.

        Returns:
            A new Logger instance with the bound context.
        """
        new_logger = Logger(self.name, self.config)
        # Bind the kwargs to the logger
        new_logger.logger = self.logger.bind(**kwargs)
        return new_logger


# Create a singleton instance of the logging service
logging_service = LoggingService()


def get_logger(name: str) -> Logger:
    """Get a logger for the given name.

    Args:
        name: The name of the logger, typically the module name.

    Returns:
        A Logger instance configured with the current settings.
    """
    return logging_service.get_logger(name)

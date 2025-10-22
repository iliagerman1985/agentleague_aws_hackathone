import asyncio
from collections.abc import MutableMapping
from typing import Any

import structlog

from common.utils import get_logger

_IGNORED_FIELDS = [
    "level",
    "logger",
    "timestamp",
    "lineno",
    "filename",
    "func_name",
    "exc_info",
]

logger = get_logger()


def notify_error(
    _logger: structlog.BoundLogger,
    _log_method: str,
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    async def send_error() -> None:
        # Extract specific variables
        message = event_dict.get("event", None)
        error = event_dict.get("exc_info", None)
        channel = event_dict.pop("channel", "bot-error")  # Remove from log if it was there, not needed for anything else
        location_id = event_dict.get("location_id", None)
        contact_id = event_dict.get("contact_id", None)

        # Format the remaining additional information
        additional_info = {k: v for k, v in event_dict.items() if k not in _IGNORED_FIELDS}
        formatted_additional_info = "\n".join(f"{k}: {v}" for k, v in additional_info.items())

        # Construct the full message
        full_message = f"{message}\nAdditional Information:\n{formatted_additional_info}"

        # Send the error message to Slack
        # await SlackNotifier.instance().send_error_message(
        #     message=full_message,
        #     error=error,
        #     channel=channel,
        #     location_id=location_id,
        #     contact_id=contact_id,
        # )

    if event_dict.get("level") == "error":
        try:
            asyncio.create_task(send_error())
        except Exception:
            # This can happen in django if there's no running event loop
            try:
                asyncio.run(send_error())
            except Exception:
                logger.exception("Error sending error to Slack")

    return event_dict

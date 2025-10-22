from logging.config import dictConfig
from typing import Any

import structlog

from common.logging.std_logging_config import StdLoggingConfig, common_logger_config
from common.utils.utils import deep_merge


def setup_logging(logging_config: dict[str, Any] | None = None) -> None:
    dictConfig(deep_merge(common_logger_config, logging_config or {}))

    structlog.configure(
        processors=StdLoggingConfig.structlog_processors,
        # `wrapper_class` is the bound logger that you get back from
        # get_logger(). This one imitates the API of `logging.Logger`.
        wrapper_class=structlog.stdlib.BoundLogger,
        # wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
        # `logger_factory` is used to create wrapped loggers that are used for
        # OUTPUT. This one returns a `logging.Logger`. The final value (a JSON
        # string) from the final processor (`JSONRenderer`) will be passed to
        # the method of the same name as that you've called on the bound logger.
        logger_factory=StdLoggingConfig.logger_factory,
        # Effectively freeze configuration after creating the first bound
        # logger.
        cache_logger_on_first_use=True,
    )

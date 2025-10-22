from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.exception_handlers import http_exception_handler as _http_exception_handler
from fastapi.exception_handlers import request_validation_exception_handler as _request_validation_exception_handler
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse

from common.core.app_error import AppException, Errors
from common.utils.msgspec import decode_json
from common.utils.utils import get_logger

logger = get_logger()


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:  # pyright: ignore
        logger.exception("Validation error", request=await _get_request_json(request), exc_info=exc)
        # with contextlib.suppress(Exception):
        #     await SlackNotifier.instance().send_bot_error(message="Validation error", error=exc)
        return await _request_validation_exception_handler(request, exc)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> Response:  # pyright: ignore
        # Only log 5xx errors as exceptions with full stack traces
        # 4xx errors (like 404) are client errors, not server errors - log as warnings
        if exc.status_code >= 500:
            logger.exception("HTTP error", request=await _get_request_json(request), exc_info=exc)
        else:
            logger.warning(
                "HTTP client error",
                status_code=exc.status_code,
                detail=exc.detail,
                path=request.url.path,
            )
        # with contextlib.suppress(Exception):
        #     await SlackNotifier.instance().send_bot_error(message="HTTP error", error=exc)
        return await _http_exception_handler(request, exc)

    @app.exception_handler(AppException)
    async def app_error_exception_handler(request: Request, exc: AppException) -> JSONResponse:  # pyright: ignore
        logger.exception("App error", request=await _get_request_json(request), exc_info=exc)
        # with contextlib.suppress(Exception):
        #     if exc.send_notification:
        #         await SlackNotifier.instance().send_error_message(
        #             message="App error",
        #             error=exc,
        #             channel=exc.reporting_channel,
        #         )
        return JSONResponse(status_code=exc.http_status or 500, content=exc.details.to_dict(mode="json"))

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:  # pyright: ignore
        logger.exception("Unhandled exception", request=await _get_request_json(request), exc_info=exc)
        # if should_send_exception_notification(exc):
        #     with contextlib.suppress(Exception):
        #         await SlackNotifier.instance().send_bot_error(message="Unhandled exception", error=exc)
        if isinstance(exc, AppException):
            return JSONResponse(status_code=exc.http_status or 500, content=exc.details.to_dict(mode="json"))
        return JSONResponse(status_code=500, content=Errors.Generic.INTERNAL_ERROR.create(cause=exc).details.to_dict(mode="json"))


async def _get_request_json(request: Request) -> dict[str, Any] | None:
    try:
        body = await request.body()
        return decode_json(body) if body else None
    except Exception:
        return None

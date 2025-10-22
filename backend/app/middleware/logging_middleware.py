"""Middleware for logging HTTP requests and responses."""

import json
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from common.utils.utils import get_logger

logger = get_logger()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses.
    Logs request details, response status, and timing information.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        # Generate a unique request ID
        request_id = str(uuid.uuid4())

        # Create a logger with request ID context
        req_logger = logger.bind(request_id=request_id)

        # Extract request details
        client_host = request.client.host if request.client else "unknown"
        request_path = request.url.path
        request_method = request.method

        # Capture request body for POST/PUT/PATCH requests
        request_body = None
        if request_method in ["POST", "PUT", "PATCH"]:
            try:
                # Read the request body
                body_bytes = await request.body()
                if body_bytes:
                    # Try to parse as JSON for better logging
                    try:
                        request_body = json.loads(body_bytes.decode("utf-8"))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        # If not JSON, log as string (truncated if too long)
                        body_str = body_bytes.decode("utf-8", errors="replace")
                        request_body = body_str[:1000] + "..." if len(body_str) > 1000 else body_str

                    # Store request body in request state for exception handlers
                    request.state.body = request_body
            except Exception as e:
                req_logger.warning(f"Failed to read request body: {e}")

        # Log the request with body if available
        log_data = {
            "type": "request_started",
            "client_ip": client_host,
            "method": request_method,
            "path": request_path,
            "query_params": str(request.query_params),
        }

        # Add request body to logs for debugging (especially for validation errors)
        if request_body is not None:
            log_data["request_body"] = request_body

        # Use debug level for GET requests (typically polling) and auth endpoints to reduce noise
        if request_method == "GET" or request_path.startswith("/api/v1/auth/"):
            req_logger.debug(f"Request started: {request_method} {request_path}", **log_data)
        else:
            req_logger.info(f"Request started: {request_method} {request_path}", **log_data)

        # Record start time
        start_time = time.time()

        try:
            # Process the request
            response: Response = await call_next(request)

            # Calculate processing time
            process_time = time.time() - start_time

            # Prepare response log data
            response_log_data = {
                "type": "request_completed",
                "method": request_method,
                "path": request_path,
                "status_code": response.status_code,
                "process_time_ms": int(round(process_time * 1000, 2)),
            }

            # For validation errors (422), include request body for debugging
            if response.status_code == 422 and request_body is not None:
                response_log_data["request_body"] = request_body
                req_logger.warning(f"Validation error: {request_method} {request_path} - {response.status_code}", **response_log_data)
            # Use debug level for successful GET requests (typically polling) and auth endpoints
            elif (request_method == "GET" and 200 <= response.status_code < 300) or (request_path.startswith("/api/v1/auth/") and 200 <= response.status_code < 300):
                req_logger.debug(f"Request completed: {request_method} {request_path} - {response.status_code}", **response_log_data)
            else:
                req_logger.info(f"Request completed: {request_method} {request_path} - {response.status_code}", **response_log_data)

            return response
        except Exception as e:
            # Calculate processing time
            process_time = time.time() - start_time

            # Prepare error log data
            error_log_data = {
                "type": "request_failed",
                "method": request_method,
                "path": request_path,
                "error": str(e),
                "process_time_ms": int(round(process_time * 1000, 2)),
            }

            # Include request body in error logs for debugging validation issues
            if request_body is not None:
                error_log_data["request_body"] = request_body

            # Log the error
            req_logger.error(
                f"Request failed: {request_method} {request_path}",
                **error_log_data,
                exc_info=True,
            )

            # Re-raise the exception
            raise

"""API routes for client error reporting."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import (
    get_current_user,
    get_db,
    get_error_report_service,
)
from app.services.error_report_service import ErrorReportService
from shared_db.schemas.error_report import (
    ErrorReportCreate,
    ErrorReportResponse,
    ErrorReportUserDetails,
)
from shared_db.schemas.user import UserResponse

error_reports_router = APIRouter()


@error_reports_router.post("/error-reports", status_code=status.HTTP_201_CREATED)
async def log_error_report(
    payload: ErrorReportCreate,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    error_report_service: Annotated[ErrorReportService, Depends(get_error_report_service)],
) -> ErrorReportResponse:
    """Persist a client error captured by the frontend."""

    request_client = request.client.host if request.client else None
    extra_metadata = {
        "referer": request.headers.get("referer"),
        "client_ip": request_client,
        "accept_language": request.headers.get("accept-language"),
    }

    user_details = ErrorReportUserDetails(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        role=current_user.role.value,
    )

    return await error_report_service.log_client_error(
        db,
        payload=payload,
        user_details=user_details,
        extra_metadata=extra_metadata,
    )

"""Service for persisting client error reports."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from common.core.config_service import ConfigService
from common.core.request_context import RequestContext
from common.utils.utils import get_logger
from shared_db.crud.error_report import ErrorReportDAO
from shared_db.schemas.error_report import (
    ErrorReportCreate,
    ErrorReportResponse,
    ErrorReportUserDetails,
)

logger = get_logger(__name__)


class ErrorReportService:
    """Business logic layer for client error reporting."""

    def __init__(self, error_report_dao: ErrorReportDAO, config_service: ConfigService | None = None) -> None:
        self._dao = error_report_dao
        self._config = config_service or ConfigService()

    async def log_client_error(
        self,
        db: AsyncSession,
        *,
        payload: ErrorReportCreate,
        user_details: ErrorReportUserDetails | None,
        extra_metadata: dict[str, Any] | None = None,
    ) -> ErrorReportResponse:
        """Persist a client-side error and return the stored representation."""

        request_context = RequestContext.get()
        metadata_overrides: dict[str, Any] = {
            "environment": self._config.get_environment(),
        }

        if request_context.request_id:
            metadata_overrides["request_id"] = str(request_context.request_id)
        if request_context.endpoint:
            metadata_overrides["endpoint"] = request_context.endpoint
        if request_context.trigger:
            metadata_overrides["trigger"] = request_context.trigger

        if extra_metadata:
            metadata_overrides.update({k: v for k, v in extra_metadata.items() if v is not None})

        report = await self._dao.create(
            db,
            payload=payload,
            user_details=user_details,
            metadata_overrides=metadata_overrides,
        )

        logger.info(
            "Stored client error report",
            extra={
                "error_report_id": str(report.id),
                "user_id": str(report.user_id) if report.user_id else None,
                "environment": metadata_overrides.get("environment"),
            },
        )

        return report

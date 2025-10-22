"""DAO for error report persistence."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.ids import ErrorReportId, UserId
from common.utils.utils import get_logger
from shared_db.models.error_report import ErrorReport
from shared_db.schemas.error_report import (
    ErrorReportCreate,
    ErrorReportResponse,
    ErrorReportUserDetails,
)

logger = get_logger(__name__)


class ErrorReportDAO:
    """Data access object for error report operations."""

    async def create(
        self,
        db: AsyncSession,
        *,
        payload: ErrorReportCreate,
        user_details: ErrorReportUserDetails | None = None,
        metadata_overrides: dict[str, Any] | None = None,
    ) -> ErrorReportResponse:
        """Persist a new error report and return the serialized response."""

        record = ErrorReport.from_create(
            payload,
            user_id=user_details.id if user_details else None,
            user_email=user_details.email if user_details else None,
            user_username=user_details.username if user_details else None,
            user_full_name=user_details.full_name if user_details else None,
            user_role=user_details.role if user_details else None,
        )

        if metadata_overrides:
            record.merge_metadata(metadata_overrides)

        db.add(record)
        await db.commit()
        await db.refresh(record)
        logger.info(
            "Persisted error report",
            extra={
                "error_report_id": str(record.id),
                "user_id": str(record.user_id) if record.user_id else None,
                "has_stack": bool(record.stack),
            },
        )
        return record.to_response()

    async def get_by_id(self, db: AsyncSession, *, error_report_id: ErrorReportId) -> ErrorReportResponse | None:
        """Fetch a single error report by its identifier."""

        result = await db.execute(select(ErrorReport).where(ErrorReport.id == error_report_id))
        record = result.scalar_one_or_none()
        return record.to_response() if record else None

    async def list_recent(
        self,
        db: AsyncSession,
        *,
        limit: int = 100,
        user_id: UserId | None = None,
    ) -> list[ErrorReportResponse]:
        """Return recent error reports, optionally filtered by user."""

        query = select(ErrorReport).order_by(ErrorReport.created_at.desc()).limit(limit)
        if user_id is not None:
            query = query.where(ErrorReport.user_id == user_id)

        result = await db.execute(query)
        records = result.scalars().all()
        return [record.to_response() for record in records]

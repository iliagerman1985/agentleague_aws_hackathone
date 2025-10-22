"""Error report model for client-side error logging."""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from common.db.db_utils import DbTSID
from common.ids import ErrorReportId, UserId
from common.utils.tsid import TSID
from shared_db.db import Base
from shared_db.schemas.error_report import ErrorReportCreate, ErrorReportResponse


class ErrorReport(Base):
    """SQLAlchemy model for persisted client error reports."""

    __tablename__ = "error_reports"

    id: Mapped[ErrorReportId] = mapped_column(DbTSID(), primary_key=True, autoincrement=False, default=TSID.create)
    user_id: Mapped[UserId | None] = mapped_column(DbTSID(), nullable=True, index=True)
    user_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    user_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    user_full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    user_role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    stack: Mapped[str | None] = mapped_column(Text, nullable=True)
    component_stack: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_payload: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)

    def merge_metadata(self, value: dict[str, Any]) -> None:
        base_metadata = self.metadata_payload or {}
        merged = {**base_metadata, **value}
        self.metadata_payload = merged

    def to_response(self) -> ErrorReportResponse:
        return ErrorReportResponse.model_validate(
            {
                "id": self.id,
                "user_id": self.user_id,
                "user_email": self.user_email,
                "user_username": self.user_username,
                "user_full_name": self.user_full_name,
                "user_role": self.user_role,
                "message": self.message,
                "name": self.name,
                "stack": self.stack,
                "component_stack": self.component_stack,
                "url": self.url,
                "user_agent": self.user_agent,
                "metadata": self.metadata_payload,
                "created_at": self.created_at,
                "updated_at": self.updated_at,
            }
        )

    @classmethod
    def from_create(
        cls,
        payload: ErrorReportCreate,
        *,
        user_id: UserId | None = None,
        user_email: str | None = None,
        user_username: str | None = None,
        user_full_name: str | None = None,
        user_role: str | None = None,
    ) -> ErrorReport:
        return cls(
            user_id=user_id,
            user_email=user_email,
            user_username=user_username,
            user_full_name=user_full_name,
            user_role=user_role,
            message=payload.message,
            name=payload.name,
            stack=payload.stack,
            component_stack=payload.component_stack,
            url=payload.url,
            user_agent=payload.user_agent,
            metadata_payload=payload.metadata,
        )

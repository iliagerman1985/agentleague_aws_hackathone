"""Tool model for user-created tools."""

from enum import StrEnum

from game_api import GameType
from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.db.db_utils import DbTSID
from common.ids import ToolId, UserId
from common.utils.tsid import TSID
from shared_db.db import Base
from shared_db.models.enum_utils import enum_values
from shared_db.models.user import User


class ToolValidationStatus(StrEnum):
    """Status of tool validation."""

    VALID = "valid"
    ERROR = "error"
    PENDING = "pending"


class Tool(Base):
    """SQLAlchemy Tool model for user-created tools."""

    __tablename__ = "tools"

    id: Mapped[ToolId] = mapped_column(DbTSID(), primary_key=True, autoincrement=False, default=TSID.create)
    user_id: Mapped[UserId | None] = mapped_column(DbTSID(), ForeignKey(User.id), nullable=True, index=True)  # Nullable for system tools
    display_name: Mapped[str] = mapped_column(String(150), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    environment: Mapped[GameType] = mapped_column(
        SAEnum(GameType, native_enum=False, values_callable=enum_values),
        nullable=False,
        index=True,
        default=GameType.TEXAS_HOLDEM,
    )
    validation_status: Mapped[ToolValidationStatus] = mapped_column(
        SAEnum(
            ToolValidationStatus,
            native_enum=False,
            values_callable=enum_values,
        ),
        nullable=False,
        server_default=ToolValidationStatus.VALID.value,
    )
    # System tool flag
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)

    # Relationships
    user = relationship("User", back_populates="tools")
    llm_usage = relationship("LLMUsage", back_populates="tool")

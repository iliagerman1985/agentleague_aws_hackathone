from enum import StrEnum

from sqlalchemy import Boolean, Enum, Integer, String, Text, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.db.db_utils import DbTSID
from common.ids import UserId
from common.utils.tsid import TSID
from shared_db.db import Base
from shared_db.models.enum_utils import enum_values


class UserRole(StrEnum):
    """User roles enum"""

    ADMIN = "admin"
    USER = "user"


class AvatarType(StrEnum):
    """Avatar type enum"""

    GOOGLE = "google"
    UPLOADED = "uploaded"
    DEFAULT = "default"


class User(Base):
    """SQLAlchemy User model"""

    __tablename__ = "users"

    id: Mapped[UserId] = mapped_column(DbTSID(), primary_key=True, autoincrement=False, default=TSID.create)
    username: Mapped[str] = mapped_column(String, unique=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    full_name: Mapped[str | None] = mapped_column(String, nullable=True)
    # Optional nickname shown in UI instead of full_name when present
    nickname: Mapped[str | None] = mapped_column(String, nullable=True, index=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=true(), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False, values_callable=enum_values),
        default=UserRole.USER,
        nullable=False,
    )
    cognito_sub: Mapped[str | None] = mapped_column(
        String,
        unique=True,
        index=True,
        nullable=True,
    )  # Cognito user ID
    coins_balance: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    # Avatar fields
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)  # Base64 encoded image or URL
    avatar_type: Mapped[AvatarType] = mapped_column(
        Enum(AvatarType, native_enum=False, values_callable=enum_values),
        default=AvatarType.DEFAULT,
        nullable=False,
    )

    # Relationships
    llm_integrations = relationship("LLMIntegration", back_populates="user")
    llm_usage = relationship("LLMUsage", back_populates="user")
    tools = relationship("Tool", back_populates="user")
    agents = relationship("Agent", back_populates="user")

    @property
    def display_name(self) -> str:
        """Return nickname if set, otherwise fall back to full_name or username."""
        if self.nickname and self.nickname.strip():
            return self.nickname
        if self.full_name and self.full_name.strip():
            return self.full_name
        return self.username

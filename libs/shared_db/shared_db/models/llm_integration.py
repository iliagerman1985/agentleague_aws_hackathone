"""LLM Integration models for storing user API keys and configurations."""

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.db.db_utils import DbTSID
from common.enums import LLMProvider
from common.ids import LLMIntegrationId, UserId
from common.utils.tsid import TSID
from shared_db.db import Base
from shared_db.models.user import User


class LLMIntegration(Base):
    """User's LLM provider integration with encrypted API key."""

    __tablename__ = "llm_integrations"

    id: Mapped[LLMIntegrationId] = mapped_column(DbTSID(), primary_key=True, autoincrement=False, default=TSID.create)
    user_id: Mapped[UserId] = mapped_column(DbTSID(), ForeignKey(User.id), nullable=False, index=True)
    provider: Mapped[LLMProvider] = mapped_column(String(20), nullable=False)  # LLMProvider enum value
    api_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)  # Encrypted API key
    selected_model: Mapped[str] = mapped_column(String(100), nullable=False)  # Model enum value
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)  # Optional custom name
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    user = relationship(User, back_populates="llm_integrations")

    # Constraints
    __table_args__ = (
        # User can have only one integration per provider
        UniqueConstraint("user_id", "provider", name="unique_user_provider"),
        # Note: Unique constraint for default integration is handled in application logic
        # since SQLite doesn't support partial unique constraints (WHERE is_default=True)
    )

    def __repr__(self) -> str:
        return f"<LLMIntegration(id={self.id}, user_id={self.user_id}, provider={self.provider}, model={self.selected_model})>"

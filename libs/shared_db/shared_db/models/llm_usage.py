"""LLM usage tracking models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.db.db_utils import DateTimeUTC, DbTSID
from common.ids import AgentVersionId, GameId, LLMUsageId, TestScenarioId, ToolId, UserId
from common.utils.tsid import TSID
from shared_db.db import Base


class LLMUsage(Base):
    """Track all LLM usage across the platform for cost analysis and debugging.

    This table logs every LLM API call made by the system, including:
    - Agent moves during games
    - Tool code generation
    - Test scenario generation
    - State generation
    - Agent instructions generation

    Each record includes the full prompt and response for debugging,
    along with token usage and cost information.
    """

    __tablename__ = "llm_usage"

    # Primary key
    id: Mapped[LLMUsageId] = mapped_column(DbTSID(), primary_key=True, autoincrement=False, default=TSID.create)

    # User who triggered this LLM usage
    user_id: Mapped[UserId] = mapped_column(DbTSID(), ForeignKey("users.id"), nullable=False, index=True)

    # Optional agent version (for agent moves)
    agent_version_id: Mapped[AgentVersionId | None] = mapped_column(DbTSID(), ForeignKey("agent_versions.id"), nullable=True, index=True)

    # Scenario tracking
    scenario: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
        comment="Type of LLM usage: agent_move, tool_generation, test_generation, state_generation, agent_instructions_generation",
    )

    # Model and cost information
    model_used: Mapped[str] = mapped_column(String, nullable=False, comment="LLM model identifier (e.g., gpt-4, claude-3-5-sonnet)")
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, comment="Cost in USD for this API call")

    # Token usage
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="Number of tokens in the prompt")
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="Number of tokens in the completion")
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="Total tokens used (input + output)")

    # Execution metadata
    execution_time_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="Time taken to execute the LLM call in milliseconds")

    # Prompts (for debugging and analysis)
    input_prompt: Mapped[str] = mapped_column(Text, nullable=False, comment="Full prompt sent to the LLM")
    output_response: Mapped[str] = mapped_column(Text, nullable=False, comment="Full response received from the LLM")

    # Optional context references
    game_id: Mapped[GameId | None] = mapped_column(DbTSID(), ForeignKey("games.id"), nullable=True, index=True)
    tool_id: Mapped[ToolId | None] = mapped_column(DbTSID(), ForeignKey("tools.id"), nullable=True, index=True)
    test_scenario_id: Mapped[TestScenarioId | None] = mapped_column(DbTSID(), ForeignKey("test_scenarios.id"), nullable=True, index=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTimeUTC, server_default=func.now(), nullable=False, index=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="llm_usage")
    agent_version: Mapped["AgentVersion"] = relationship("AgentVersion", back_populates="llm_usage")
    game: Mapped["Game"] = relationship("Game", back_populates="llm_usage")
    tool: Mapped["Tool"] = relationship("Tool", back_populates="llm_usage")
    test_scenario: Mapped["TestScenario"] = relationship("TestScenario", back_populates="llm_usage")

    # Indexes for common queries
    __table_args__ = (
        Index("ix_llm_usage_user_created", "user_id", "created_at"),
        Index("ix_llm_usage_agent_created", "agent_version_id", "created_at"),
        Index("ix_llm_usage_scenario_created", "scenario", "created_at"),
        Index("ix_llm_usage_game_created", "game_id", "created_at"),
    )

    def __repr__(self) -> str:
        """String representation of LLM usage."""
        return (
            f"<LLMUsage(id={self.id}, user_id={self.user_id}, scenario={self.scenario}, "
            f"model={self.model_used}, cost=${self.cost_usd:.4f}, tokens={self.total_tokens})>"
        )

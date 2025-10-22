"""Agent models for user-created AI agents."""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast

from game_api import GameType
from pydantic import Field
from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.db.db_utils import DateTimeUTC, DbTSID
from common.ids import (
    AgentExecutionSessionId,
    AgentId,
    AgentIterationHistoryId,
    AgentStatisticsId,
    AgentVersionId,
    AgentVersionToolId,
    GameId,
    TestScenarioId,
    TestScenarioResultId,
    ToolId,
    UserId,
)
from common.utils import JsonModel
from common.utils.tsid import TSID
from shared_db.db import Base
from shared_db.models.enum_utils import enum_values
from shared_db.models.tool import Tool
from shared_db.models.user import AvatarType, User


# Pydantic schemas for JSON fields to avoid using Any types
class RecentGameEntry(JsonModel):
    """Entry for recent game performance tracking."""

    game_id: str | None = Field(default=None, description="Game ID if available")
    game_type: str = Field(description="Type of game (chess, texas_holdem, etc.)")
    result: str = Field(description="Game result: win, loss, or draw")
    rating_change: float = Field(description="Rating change from this game")
    rating_after: float = Field(description="Rating after this game")
    timestamp: str = Field(description="ISO timestamp of when the game ended")


class AgentGameRating(JsonModel):
    """Agent rating and statistics for a specific game type."""

    rating: float = Field(description="Current rating for the game")
    games_played: int = Field(default=0, description="Total games played")
    games_won: int = Field(default=0, description="Games won")
    games_lost: int = Field(default=0, description="Games lost")
    games_drawn: int = Field(default=0, description="Games drawn")
    highest_rating: float = Field(description="Highest rating achieved")
    lowest_rating: float = Field(description="Lowest rating achieved")


class AgentStatisticsData(JsonModel):
    """Game/environment agnostic structured data for agent statistics.

    Game-specific ratings and statistics are stored dynamically in the game_ratings field
    to support any number of games without requiring schema changes.
    """

    # Core game-agnostic statistics
    games_played: int = Field(default=0, description="Total number of games played")
    total_winnings: float = Field(default=0.0, description="Total winnings across all games")
    total_losses: float = Field(default=0.0, description="Total losses across all games")
    net_balance: float = Field(default=0.0, description="Current net balance (winnings - losses)")
    win_rate: float = Field(default=0.0, description="Win rate percentage")
    games_won: int = Field(default=0, description="Number of games won")
    games_lost: int = Field(default=0, description="Number of games lost")
    games_drawn: int = Field(default=0, description="Number of games drawn")
    session_time_seconds: int = Field(default=0, description="Total session time in seconds (real games only)")
    longest_game_seconds: int = Field(default=0, description="Duration of longest game in seconds")
    shortest_game_seconds: int | None = Field(default=None, description="Duration of shortest game in seconds")

    # Dynamic game-specific ratings and statistics
    # Structure: {GameType.CHESS: AgentGameRating, GameType.TEXAS_HOLDEM: AgentGameRating, ...}
    game_ratings: dict[GameType, AgentGameRating] = Field(default_factory=dict, description="Game-specific ratings and statistics keyed by GameType")

    # Recent performance tracking (last 10 games across all games)
    recent_form: list[RecentGameEntry] = Field(default_factory=list, description="Recent game results (last 10 games) with game_type, result, rating_change")

    # Environment-specific data as JSON - to be parsed by agent based on game environment
    environment_specific_data: dict[str, Any] = Field(default_factory=dict, description="Environment-specific metrics (e.g., poker hands, chess moves, etc.)")

    # Custom metrics for extensibility
    custom_metrics: dict[str, float] = Field(default_factory=dict, description="Custom metrics")


class Agent(Base):
    """SQLAlchemy Agent model for user-created AI agents.

    Each agent can have up to 10 versions. When creating the 11th version,
    the oldest version should be deleted to maintain the limit.
    """

    __tablename__ = "agents"

    # Maximum number of versions per agent
    MAX_VERSIONS = 10

    id: Mapped[AgentId] = mapped_column(DbTSID(), primary_key=True, autoincrement=False, default=TSID.create)
    user_id: Mapped[UserId | None] = mapped_column(DbTSID(), ForeignKey(User.id), nullable=True, index=True)  # Nullable for system agents
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    game_environment: Mapped[GameType] = mapped_column(String(50), nullable=False)  # GameType enum value - immutable after creation
    auto_buy: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)  # Whether agent auto-buys chips (poker-specific)
    auto_reenter: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # Whether agent automatically re-enters games
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)  # Whether agent is active for deployment
    # Soft archive fields
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTimeUTC(), nullable=True)
    # System agent flag
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    # Matchmaking filter flag
    can_play_in_real_matches: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)

    # Avatar fields
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)  # Base64 encoded image or URL
    avatar_type: Mapped[AvatarType] = mapped_column(
        Enum(AvatarType, native_enum=False, values_callable=enum_values),
        default=AvatarType.DEFAULT,
        nullable=False,
    )

    # Relationships
    user = relationship(User, back_populates="agents")
    versions = relationship("AgentVersion", back_populates="agent", cascade="all, delete-orphan", order_by="AgentVersion.version_number")
    statistics = relationship("AgentStatistics", back_populates="agent", uselist=False, cascade="all, delete-orphan")

    def get_version_count(self) -> int:
        """Get the current number of versions for this agent."""
        return len(self.versions)

    def can_create_new_version(self) -> bool:
        """Check if a new version can be created (under the limit)."""
        return self.get_version_count() < self.MAX_VERSIONS

    def get_oldest_version(self) -> AgentVersion | None:
        """Get the oldest version (lowest version number)."""
        if not self.versions:
            return None
        return min(self.versions, key=lambda v: v.version_number)

    def get_latest_version(self) -> AgentVersion | None:
        """Get the latest version (highest version number)."""
        if not self.versions:
            return None
        return max(self.versions, key=lambda v: v.version_number)

    def get_active_version(self) -> AgentVersion | None:
        """Get the currently active version."""
        for version in self.versions:
            if version.is_active:
                return version
        return None


class AgentVersion(Base):
    """SQLAlchemy AgentVersion model for versioned agent configurations.

    A new version is created when any of these change:
    - system_prompt (core agent instructions)
    - conversation_instructions (behavior rules)
    - exit_criteria (when to stop execution)
    - tools (added, removed, or reordered tools)

    Configuration changes (timeout, max_iterations, LLM IDs) do NOT create new versions.
    """

    __tablename__ = "agent_versions"

    id: Mapped[AgentVersionId] = mapped_column(DbTSID(), primary_key=True, autoincrement=False, default=TSID.create)
    agent_id: Mapped[AgentId] = mapped_column(ForeignKey(Agent.id), nullable=False, index=True)
    user_id: Mapped[UserId] = mapped_column(ForeignKey(User.id), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)  # Auto-incremented version number

    # VERSION-DEFINING FIELDS (changes trigger new version)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)  # System prompt with template variables
    conversation_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)  # Agent behavior rules
    exit_criteria: Mapped[str | None] = mapped_column(Text, nullable=True)  # When to stop execution
    # tools are defined in AgentVersionTool relationship

    # CONFIGURATION FIELDS (changes update current version)
    slow_llm_provider: Mapped[str] = mapped_column(String(20), nullable=False)  # LLMProvider enum value
    fast_llm_provider: Mapped[str] = mapped_column(String(20), nullable=False)  # LLMProvider enum value
    slow_llm_model: Mapped[str | None] = mapped_column(String(100), nullable=True)  # Optional model override
    fast_llm_model: Mapped[str | None] = mapped_column(String(100), nullable=True)  # Optional model override
    timeout: Mapped[int] = mapped_column(Integer, default=300, nullable=False)  # Execution timeout in seconds
    max_iterations: Mapped[int] = mapped_column(Integer, default=10, nullable=False)  # Max tool iterations per decision

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)  # Whether this version is active

    # Relationships
    agent = relationship(Agent, back_populates="versions")
    tools = relationship("AgentVersionTool", back_populates="agent_version", cascade="all, delete-orphan")
    llm_usage = relationship("LLMUsage", back_populates="agent_version")

    # Constraints
    __table_args__ = (
        # Each agent can have only one version with a specific version number
        UniqueConstraint("agent_id", "version_number", name="unique_agent_version"),
        # Only one active version per agent (handled in application logic)
    )

    def get_version_defining_fields(self) -> dict[str, Any]:
        """Get fields that define a version (changes trigger new version)."""
        return {
            "system_prompt": self.system_prompt,
            "conversation_instructions": self.conversation_instructions,
            "exit_criteria": self.exit_criteria,
            "tool_ids": [tool.tool_id for tool in sorted(self.tools, key=lambda t: t.order)],
        }

    def get_configuration_fields(self) -> dict[str, Any]:
        """Get configuration fields (changes update current version)."""
        return {
            "slow_llm_provider": self.slow_llm_provider,
            "fast_llm_provider": self.fast_llm_provider,
            "slow_llm_model": self.slow_llm_model,
            "fast_llm_model": self.fast_llm_model,
            "timeout": self.timeout,
            "max_iterations": self.max_iterations,
        }


class AgentVersionTool(Base):
    """Junction table for agent version to tool relationships with ordering."""

    __tablename__ = "agent_version_tools"

    id: Mapped[AgentVersionToolId] = mapped_column(DbTSID(), primary_key=True, autoincrement=False, default=TSID.create)
    agent_version_id: Mapped[AgentVersionId] = mapped_column(ForeignKey(AgentVersion.id), nullable=False, index=True)
    tool_id: Mapped[ToolId] = mapped_column(ForeignKey(Tool.id), nullable=False, index=True)
    order: Mapped[int] = mapped_column(Integer, nullable=False)  # Tool execution order (0-based)

    # Relationships
    agent_version = relationship(AgentVersion, back_populates="tools")
    tool = relationship(Tool)

    # Constraints
    __table_args__ = (
        # Each agent version can have a tool only once
        UniqueConstraint("agent_version_id", "tool_id", name="unique_agent_version_tool"),
        # Each agent version can have only one tool at each order position
        UniqueConstraint("agent_version_id", "order", name="unique_agent_version_tool_order"),
    )


class AgentStatistics(Base):
    """SQLAlchemy AgentStatistics model for tracking agent performance."""

    __tablename__ = "agent_statistics"

    id: Mapped[AgentStatisticsId] = mapped_column(DbTSID(), primary_key=True, autoincrement=False, default=TSID.create)
    agent_id: Mapped[AgentId] = mapped_column(ForeignKey(Agent.id), nullable=False, index=True, unique=True)
    statistics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)  # JSON structure following AgentStatisticsData schema

    # Relationships
    agent = relationship(Agent, back_populates="statistics")

    def get_statistics_data(self) -> AgentStatisticsData:
        """Get statistics as a typed Pydantic model."""
        return AgentStatisticsData.model_validate(self.statistics)

    def set_statistics_data(self, data: AgentStatisticsData) -> None:
        """Set statistics from a typed Pydantic model."""
        self.statistics = data.model_dump()

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics as a plain dictionary."""
        # Cast to handle SQLAlchemy descriptor magic - at runtime this is the actual value
        stats_data = cast("dict[str, Any] | None", self.statistics)
        if stats_data is None:
            # Return default statistics
            return AgentStatisticsData().model_dump()
        return stats_data

    def set_statistics(self, statistics: dict[str, Any]) -> None:
        """Set statistics from a plain dictionary."""
        self.statistics = statistics


class TestScenario(Base):
    """SQLAlchemy TestScenario model for synthetic test data."""

    __tablename__ = "test_scenarios"

    id: Mapped[TestScenarioId] = mapped_column(DbTSID(), primary_key=True, autoincrement=False, default=TSID.create)
    user_id: Mapped[UserId | None] = mapped_column(DbTSID(), ForeignKey(User.id), nullable=True, index=True)  # Nullable for system scenarios
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    environment: Mapped[GameType] = mapped_column(String(50), nullable=False)  # GameType enum value
    game_state: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)  # Synthetic environment state data (flexible for different games)
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=True)  # JSON array following TestScenarioTags schema
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)  # System-wide predefined scenarios

    # Relationships
    user = relationship(User)
    results = relationship("TestScenarioResult", back_populates="test_scenario", cascade="all, delete-orphan")
    llm_usage = relationship("LLMUsage", back_populates="test_scenario")

    def get_tags(self) -> list[str]:
        """Get tags as a simple list."""
        tags_data = getattr(self, "tags", None)
        return tags_data or []

    def set_tags(self, tags: list[str]) -> None:
        """Set tags from a simple list."""
        self.tags = tags


class TestScenarioResult(Base):
    """Aggregated results for a test scenario execution."""

    __tablename__ = "test_scenario_results"

    id: Mapped[TestScenarioResultId] = mapped_column(DbTSID(), primary_key=True, autoincrement=False, default=TSID.create)
    test_scenario_id: Mapped[TestScenarioId] = mapped_column(ForeignKey(TestScenario.id), nullable=False, index=True)
    agent_version_id: Mapped[AgentVersionId] = mapped_column(ForeignKey(AgentVersion.id), nullable=False, index=True)

    # Aggregated results
    total_execution_sessions: Mapped[int] = mapped_column(Integer, nullable=False, default=1)  # Number of moves/decisions made
    successful_sessions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_sessions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Performance metrics
    total_execution_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    average_iterations_per_session: Mapped[int] = mapped_column(Integer, nullable=False)
    total_validation_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Outcome summary
    final_outcome: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)  # Game result or test outcome
    score: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)  # Score/metrics specific to the test

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    test_scenario = relationship(TestScenario, back_populates="results")
    agent_version = relationship(AgentVersion)
    execution_sessions = relationship("AgentExecutionSession", back_populates="test_scenario_result", cascade="all, delete-orphan")


class AgentExecutionSession(Base):
    """Groups iterations for a single decision/move by an agent.

    This allows querying:
    - All iterations for a specific game (filter by game_id)
    - All iterations for a specific agent version (filter by agent_version_id)
    - All iterations for a specific test scenario (filter by test_scenario_id)
    - Iterations grouped by move/hand number (order by move_number)
    """

    __tablename__ = "agent_execution_sessions"
    __table_args__ = (
        # Composite indexes for common query patterns
        Index("idx_game_move", "game_id", "move_number"),
        Index("idx_version_game", "agent_version_id", "game_id"),
        Index("idx_version_test", "agent_version_id", "test_scenario_id"),
    )

    id: Mapped[AgentExecutionSessionId] = mapped_column(DbTSID(), primary_key=True, autoincrement=False, default=TSID.create)
    agent_version_id: Mapped[AgentVersionId] = mapped_column(ForeignKey(AgentVersion.id), nullable=False, index=True)

    # Context fields for different execution types
    execution_type: Mapped[str] = mapped_column(String, nullable=False, index=True)  # 'test_scenario', 'manual_test', 'live_game'
    game_id: Mapped[GameId | None] = mapped_column(DbTSID(), nullable=True, index=True)  # External game ID for live games
    test_scenario_id: Mapped[TestScenarioId | None] = mapped_column(ForeignKey(TestScenario.id), nullable=True, index=True)
    test_scenario_result_id: Mapped[TestScenarioResultId | None] = mapped_column(ForeignKey(TestScenarioResult.id), nullable=True, index=True)

    # Session metadata
    move_number: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)  # Move/turn/hand number in a game
    game_state_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)  # Game state at start of decision

    # Outcome
    final_action: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)  # Final action decided
    final_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)  # Final reasoning
    total_iterations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    execution_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    validation_attempts: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)  # Whether execution completed successfully

    # Aggregated token usage and cost tracking for the entire session
    total_input_tokens: Mapped[int] = mapped_column(Integer, nullable=True, default=0)  # Sum of all prompt tokens
    total_output_tokens: Mapped[int] = mapped_column(Integer, nullable=True, default=0)  # Sum of all completion tokens
    total_tokens_used: Mapped[int] = mapped_column(Integer, nullable=True, default=0)  # Sum of all tokens used
    total_cost_usd: Mapped[float] = mapped_column(Float, nullable=True, default=0.0)  # Total cost in USD for the session

    # Relationships
    agent_version = relationship(AgentVersion)
    test_scenario = relationship(TestScenario)
    test_scenario_result = relationship(TestScenarioResult, back_populates="execution_sessions")
    iterations = relationship("AgentIterationHistory", back_populates="execution_session", cascade="all, delete-orphan")


class AgentIterationHistory(Base):
    """Individual iteration steps within an execution session."""

    __tablename__ = "agent_iteration_history"

    id: Mapped[AgentIterationHistoryId] = mapped_column(DbTSID(), primary_key=True, autoincrement=False, default=TSID.create)
    execution_session_id: Mapped[AgentExecutionSessionId] = mapped_column(ForeignKey(AgentExecutionSession.id), nullable=False, index=True)
    iteration_number: Mapped[int] = mapped_column(Integer, nullable=False)  # Iteration number within the session

    # Iteration details
    role: Mapped[str] = mapped_column(String, nullable=False)  # 'system', 'user', 'assistant', 'tool'
    content: Mapped[str] = mapped_column(Text, nullable=False)  # Message content
    tool_name: Mapped[str | None] = mapped_column(String, nullable=True)  # Tool name if role is tool
    tool_parameters: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)  # Tool parameters if role is tool

    # Assistant response details (when role='assistant')
    next_step_type: Mapped[str | None] = mapped_column(String, nullable=True)  # 'tool', 'final', 'validation_retry'
    next_step_details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)  # Details about next step

    # Execution metadata
    llm_model: Mapped[str | None] = mapped_column(String, nullable=True)  # Which LLM was used
    execution_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Token usage and cost tracking
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Prompt tokens
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Completion tokens
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Total tokens used
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)  # Cost in USD for this iteration

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)  # If iteration failed

    # Relationships
    execution_session = relationship(AgentExecutionSession, back_populates="iterations")

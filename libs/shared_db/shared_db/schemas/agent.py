"""Agent schemas for API requests and responses."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from game_api import GameId, GameType
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_serializer

from common.enums import LLMProvider
from common.ids import (
    AgentExecutionSessionId,
    AgentId,
    AgentIterationHistoryId,
    AgentStatisticsId,
    AgentVersionId,
    LLMIntegrationId,
    TestScenarioId,
    TestScenarioResultId,
    ToolId,
    UserId,
)
from common.types import AgentReasoning
from common.utils.json_model import JsonModel
from shared_db.models.agent import AgentStatisticsData
from shared_db.models.user import AvatarType

if TYPE_CHECKING:
    # Type alias for all supported agent input types
    # Import here to avoid circular imports - will be expanded when we add more games
    from shared_db.schemas.game_environments import TexasHoldemAgentInput

    # Union of all supported input types - expand this when adding new games
    AgentInput = TexasHoldemAgentInput

# Import for runtime use
from shared_db.schemas.game_environments import AgentIterationHistoryEntry, ToolCallParameters


class AgentBase(JsonModel):
    """Base agent schema with common fields."""

    name: str = Field(..., min_length=1, max_length=100, description="Agent name")
    description: str | None = Field(default=None, description="Agent description")
    game_environment: GameType = Field(..., description="Game environment (immutable after creation)")
    auto_buy: bool = Field(default=True, description="Whether agent auto-buys chips (poker-specific)")
    auto_reenter: bool = Field(default=False, description="Whether agent automatically re-enters games")
    is_active: bool = Field(default=True, description="Whether agent is active for deployment")
    avatar_url: str | None = Field(default=None, description="Agent avatar URL")
    avatar_type: AvatarType | None = Field(default=AvatarType.DEFAULT, description="Agent avatar type")


class AgentCreate(AgentBase):
    """Schema for creating a new agent."""


class AgentUpdate(BaseModel):
    """Schema for updating an agent."""

    name: str | None = Field(default=None, min_length=1, max_length=100, description="Agent name")
    description: str | None = Field(default=None, description="Agent description")
    # game_environment is immutable after creation
    auto_buy: bool | None = Field(default=None, description="Whether agent auto-buys chips")
    auto_reenter: bool | None = Field(default=None, description="Whether agent automatically re-enters games")
    is_active: bool | None = Field(default=None, description="Whether agent is active")
    avatar_url: str | None = Field(default=None, description="Agent avatar URL")
    avatar_type: AvatarType | None = Field(default=None, description="Agent avatar type")


class AgentResponse(AgentBase):
    """Schema for agent responses."""

    model_config = ConfigDict(from_attributes=True)

    id: AgentId
    user_id: UserId | None
    created_at: datetime
    updated_at: datetime
    # Soft archive
    is_archived: bool = Field(default=False, description="Whether the agent is soft-archived")
    archived_at: datetime | None = Field(default=None, description="Timestamp when the agent was archived")
    # System agent flag
    is_system: bool = Field(default=False, description="Whether this is a system-wide agent available to all users")


class AgentInDB(AgentResponse):
    """Schema for agent data as stored in database."""


# Agent Version Schemas
class AgentVersionDefiningFields(JsonModel):
    """Fields that define a version - changes trigger new version creation."""

    system_prompt: str = Field(..., min_length=1, description="System prompt with template variables")
    conversation_instructions: str | None = Field(default=None, description="Agent behavior rules")
    exit_criteria: str | None = Field(default=None, description="When to stop execution")
    tool_ids: list[ToolId] = Field(..., min_length=0, max_length=10, description="List of tool IDs (0-10 tools)")

    @field_validator("tool_ids")
    @classmethod
    def validate_tool_ids(cls, v: list[ToolId]) -> list[ToolId]:
        """Validate tool IDs list (0-10, unique)."""
        if len(v) > 10:
            raise ValueError("Agent must have between 0 and 10 tools")
        if len(set(v)) != len(v):
            raise ValueError("Tool IDs must be unique")
        return v


class AgentVersionConfigurationFields(JsonModel):
    """Configuration fields - changes update current version without creating new version."""

    slow_llm_provider: LLMProvider = Field(..., description="LLM provider for complex reasoning")
    fast_llm_provider: LLMProvider = Field(..., description="LLM provider for quick responses")
    slow_llm_model: str | None = Field(default=None, description="Optional model override for slow provider")
    fast_llm_model: str | None = Field(default=None, description="Optional model override for fast provider")
    timeout: int = Field(default=300, ge=1, le=300, description="Execution timeout in seconds")
    max_iterations: int = Field(default=10, ge=1, le=50, description="Max tool iterations per decision")


class AgentVersionBase(AgentVersionDefiningFields, AgentVersionConfigurationFields):
    """Base agent version schema combining version-defining and configuration fields."""


class AgentVersionCreate(AgentVersionBase):
    """Schema for creating a new agent version.

    Note: Each agent can have up to 10 versions. When creating the 11th version,
    the oldest version will be automatically deleted.
    """


class AgentVersionUpdate(BaseModel):
    """Schema for updating an agent version (determines if new version is needed)."""

    # Version-defining fields (changes trigger new version)
    system_prompt: str | None = Field(default=None, min_length=1, description="System prompt")
    conversation_instructions: str | None = Field(default=None, description="Agent behavior rules")
    exit_criteria: str | None = Field(default=None, description="When to stop execution")
    tool_ids: list[ToolId] | None = Field(default=None, min_length=0, max_length=10, description="List of tool IDs")

    # Configuration fields (changes update current version)
    slow_llm_provider: LLMProvider | None = Field(default=None, description="LLM provider for complex reasoning")
    fast_llm_provider: LLMProvider | None = Field(default=None, description="LLM provider for quick responses")
    slow_llm_model: str | None = Field(default=None, description="Optional model override for slow provider")
    fast_llm_model: str | None = Field(default=None, description="Optional model override for fast provider")
    timeout: int | None = Field(default=None, ge=1, le=300, description="Execution timeout in seconds")
    max_iterations: int | None = Field(default=None, ge=1, le=50, description="Max tool iterations per decision")

    @field_validator("tool_ids")
    @classmethod
    def validate_tool_ids(cls, v: list[ToolId] | None) -> list[ToolId] | None:
        """Validate tool IDs list (0-10, unique)."""
        if v is None:
            return v
        if len(v) > 10:
            raise ValueError("Agent must have between 0 and 10 tools")
        if len(set(v)) != len(v):
            raise ValueError("Tool IDs must be unique")
        return v

    def has_version_defining_changes(self) -> bool:
        """Check if this update contains version-defining changes."""
        return any([self.system_prompt is not None, self.conversation_instructions is not None, self.exit_criteria is not None, self.tool_ids is not None])

    def get_version_defining_fields(self) -> dict[str, Any]:
        """Get only the version-defining fields that are set."""
        fields: dict[str, Any] = {}
        if self.system_prompt is not None:
            fields["system_prompt"] = self.system_prompt
        if self.conversation_instructions is not None:
            fields["conversation_instructions"] = self.conversation_instructions
        if self.exit_criteria is not None:
            fields["exit_criteria"] = self.exit_criteria
        if self.tool_ids is not None:
            fields["tool_ids"] = self.tool_ids
        return fields

    def get_configuration_fields(self) -> dict[str, Any]:
        """Get only the configuration fields that are set."""
        fields: dict[str, Any] = {}
        if self.slow_llm_provider is not None:
            fields["slow_llm_provider"] = self.slow_llm_provider
        if self.fast_llm_provider is not None:
            fields["fast_llm_provider"] = self.fast_llm_provider
        if self.slow_llm_model is not None:
            fields["slow_llm_model"] = self.slow_llm_model
        if self.fast_llm_model is not None:
            fields["fast_llm_model"] = self.fast_llm_model
        if self.timeout is not None:
            fields["timeout"] = self.timeout
        if self.max_iterations is not None:
            fields["max_iterations"] = self.max_iterations
        return fields


class AgentVersionResponse(AgentVersionBase):
    """Schema for agent version responses."""

    model_config = ConfigDict(from_attributes=True)

    # Override to allow default when validating from ORM; DAO fills real values when needed
    tool_ids: list[ToolId] = Field(default_factory=list, description="List of tool IDs")

    id: AgentVersionId
    agent_id: AgentId
    user_id: UserId
    version_number: int
    is_active: bool
    created_at: datetime
    game_environment: str | None = Field(default=None, description="Game environment from parent agent")


class AgentVersionInDB(AgentVersionResponse):
    """Schema for agent version data as stored in database."""


# Test Scenario Schemas
class TestScenarioBase(JsonModel):
    """Base test scenario schema with common fields."""

    name: str = Field(..., min_length=1, max_length=200, description="Test scenario name")
    description: str | None = Field(default=None, description="Test scenario description")
    environment: GameType = Field(..., description="Game environment")
    game_state: dict[str, Any] = Field(..., description="Synthetic environment state data")
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")
    is_system: bool = Field(default=False, description="Whether this is a system-wide predefined scenario")


class TestScenarioCreate(TestScenarioBase):
    """Schema for creating a new test scenario."""


class TestScenarioUpdate(BaseModel):
    """Schema for updating a test scenario."""

    name: str | None = Field(default=None, min_length=1, max_length=200, description="Test scenario name")
    description: str | None = Field(default=None, description="Test scenario description")
    game_state: dict[str, Any] | None = Field(default=None, description="Synthetic environment state data")
    tags: list[str] | None = Field(default=None, description="Tags for categorization")


class TestScenarioResponse(TestScenarioBase, JsonModel):
    """Schema for test scenario responses."""

    model_config = ConfigDict(from_attributes=True)

    id: TestScenarioId
    user_id: UserId | None  # Nullable for system scenarios
    created_at: datetime
    updated_at: datetime


class TestScenarioInDB(TestScenarioResponse):
    """Schema for test scenario data as stored in database."""


# Game State Management Schemas
class SaveGameStateRequest(BaseModel):
    """Schema for saving a game state as a test scenario."""

    name: str = Field(..., min_length=1, max_length=200, description="Name for the saved game state")
    description: str | None = Field(default=None, description="Optional description")
    game_state: dict[str, Any] = Field(..., description="Game state JSON to save")
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")


class AgentStatisticsResponse(JsonModel):
    """Schema for agent statistics responses."""

    model_config = ConfigDict(from_attributes=True)

    id: AgentStatisticsId
    agent_id: AgentId
    statistics: "AgentStatisticsData"  # Properly typed statistics data with camelCase serialization
    updated_at: datetime


# Version Management Schemas
class AgentVersionRollbackRequest(BaseModel):
    """Schema for rolling back to a previous agent version."""

    target_version_number: int = Field(..., ge=1, description="Version number to rollback to")


class AgentVersionLimitInfo(JsonModel):
    """Schema for agent version limit information."""

    current_version_count: int = Field(..., ge=0, le=10, description="Current number of versions")
    max_versions: int = Field(default=10, description="Maximum allowed versions")
    can_create_new_version: bool = Field(..., description="Whether a new version can be created")
    oldest_version_number: int | None = Field(default=None, description="Version number of oldest version (will be deleted if at limit)")
    latest_version_number: int | None = Field(default=None, description="Version number of latest version")
    active_version_number: int | None = Field(default=None, description="Version number of currently active version")


class AgentVersionDifference(JsonModel):
    """Schema for a single field difference between versions."""

    field_name: str = Field(..., description="Name of the field that changed")
    old_value: Any = Field(..., description="Previous value")
    new_value: Any = Field(..., description="New value")
    change_type: str = Field(..., description="Type of change: version_defining or configuration")


class AgentVersionComparisonResponse(JsonModel):
    """Schema for comparing two agent versions."""

    version_a: AgentVersionResponse
    version_b: AgentVersionResponse
    differences: list[AgentVersionDifference] = Field(..., description="List of differences between versions")
    requires_new_version: bool = Field(..., description="Whether differences require a new version")

    @classmethod
    def compare_versions(cls, version_a: AgentVersionResponse, version_b: AgentVersionResponse) -> "AgentVersionComparisonResponse":
        """Compare two agent versions and identify differences."""
        differences: list[AgentVersionDifference] = []

        # Version-defining fields
        version_defining_fields = [
            ("system_prompt", "version_defining"),
            ("conversation_instructions", "version_defining"),
            ("exit_criteria", "version_defining"),
            ("tool_ids", "version_defining"),
        ]

        # Configuration fields
        configuration_fields = [
            ("slow_llm_provider", "configuration"),
            ("fast_llm_provider", "configuration"),
            ("slow_llm_model", "configuration"),
            ("fast_llm_model", "configuration"),
            ("timeout", "configuration"),
            ("max_iterations", "configuration"),
        ]

        all_fields = version_defining_fields + configuration_fields

        for field_name, change_type in all_fields:
            old_value = getattr(version_a, field_name, None)
            new_value = getattr(version_b, field_name, None)

            if old_value != new_value:
                differences.append(AgentVersionDifference(field_name=field_name, old_value=old_value, new_value=new_value, change_type=change_type))

        # Check if any version-defining fields changed
        requires_new_version = any(diff.change_type == "version_defining" for diff in differences)

        return cls(version_a=version_a, version_b=version_b, differences=differences, requires_new_version=requires_new_version)


# Execution Session Schemas
class AgentIterationHistoryCreate(BaseModel):
    """Schema for creating an iteration history entry."""

    iteration_number: int = Field(..., description="Iteration number within the session")
    role: str = Field(..., description="Message role: system, user, assistant, tool")
    content: str = Field(..., description="Message content")
    tool_name: str | None = Field(default=None, description="Tool name if role is tool")
    tool_parameters: dict[str, Any] | None = Field(default=None, description="Tool parameters")
    next_step_type: str | None = Field(default=None, description="Next step type: tool, final, validation_retry")
    next_step_details: dict[str, Any] | None = Field(default=None, description="Next step details")
    llm_model: str | None = Field(default=None, description="LLM model used")
    execution_time_ms: int | None = Field(default=None, description="Execution time for this iteration")

    # Token usage and cost tracking
    input_tokens: int | None = Field(default=None, description="Prompt tokens used")
    output_tokens: int | None = Field(default=None, description="Completion tokens used")
    total_tokens: int | None = Field(default=None, description="Total tokens used")
    cost_usd: float | None = Field(default=None, description="Cost in USD for this iteration")

    # Legacy field - kept for backward compatibility
    tokens_used: int | None = Field(default=None, description="Tokens used (legacy)")

    error_message: str | None = Field(default=None, description="Error message if failed")


class AgentIterationHistoryResponse(JsonModel):
    """Schema for iteration history responses."""

    model_config = ConfigDict(from_attributes=True)

    id: AgentIterationHistoryId
    execution_session_id: AgentExecutionSessionId
    iteration_number: int
    role: str
    content: str
    tool_name: str | None
    tool_parameters: dict[str, Any] | None
    next_step_type: str | None
    next_step_details: dict[str, Any] | None
    llm_model: str | None
    execution_time_ms: int | None

    # Token usage and cost tracking
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    cost_usd: float | None

    # Legacy field - kept for backward compatibility
    tokens_used: int | None

    error_message: str | None
    created_at: datetime


class AgentExecutionSessionCreate(BaseModel):
    """Schema for creating an execution session."""

    agent_version_id: AgentVersionId = Field(..., description="Agent version ID")
    execution_type: str = Field(..., description="Type: test_scenario, manual_test, live_game")
    game_id: GameId | None = Field(default=None, description="External game ID for live games")
    test_scenario_id: TestScenarioId | None = Field(default=None, description="Test scenario ID if applicable")
    test_scenario_result_id: TestScenarioResultId | None = Field(default=None, description="Test scenario result ID if applicable")
    move_number: int | None = Field(default=None, description="Move/hand number in game")
    game_state_snapshot: dict[str, Any] = Field(..., description="Game state at decision time")
    final_action: dict[str, Any] = Field(..., description="Final action decided")
    final_reasoning: str | None = Field(default=None, description="Final reasoning")
    total_iterations: int = Field(default=0, description="Total iterations in session")
    execution_time_ms: int = Field(..., description="Total execution time")
    validation_attempts: int = Field(default=1, description="Validation attempts")
    success: bool = Field(default=True, description="Whether execution succeeded")

    # Aggregated token usage and cost tracking for the entire session
    total_input_tokens: int = Field(default=0, description="Sum of all prompt tokens")
    total_output_tokens: int = Field(default=0, description="Sum of all completion tokens")
    total_tokens_used: int = Field(default=0, description="Sum of all tokens used")
    total_cost_usd: float = Field(default=0.0, description="Total cost in USD for the session")


class AgentExecutionSessionResponse(JsonModel):
    """Schema for execution session responses."""

    model_config = ConfigDict(from_attributes=True)

    id: AgentExecutionSessionId
    agent_version_id: AgentVersionId
    execution_type: str
    game_id: GameId | None
    test_scenario_id: TestScenarioId | None
    test_scenario_result_id: TestScenarioResultId | None
    move_number: int | None
    game_state_snapshot: dict[str, Any]
    final_action: dict[str, Any]
    final_reasoning: str | None
    total_iterations: int
    execution_time_ms: int
    validation_attempts: int
    success: bool
    created_at: datetime

    # Aggregated token usage and cost tracking for the entire session
    total_input_tokens: int | None
    total_output_tokens: int | None
    total_tokens_used: int | None
    total_cost_usd: float | None

    iterations: list[AgentIterationHistoryResponse] | None = Field(default=None, description="Iteration history if loaded")


class TestScenarioResultCreate(BaseModel):
    """Schema for creating a test scenario result."""

    test_scenario_id: TestScenarioId = Field(..., description="Test scenario ID")
    agent_version_id: AgentVersionId = Field(..., description="Agent version ID")
    total_execution_sessions: int = Field(default=1, description="Number of moves/decisions")
    successful_sessions: int = Field(default=0, description="Successful sessions")
    failed_sessions: int = Field(default=0, description="Failed sessions")
    total_execution_time_ms: int = Field(..., description="Total execution time")
    average_iterations_per_session: int = Field(..., description="Average iterations per session")
    total_validation_attempts: int = Field(default=1, description="Total validation attempts")
    final_outcome: dict[str, Any] | None = Field(default=None, description="Final game/test outcome")
    score: dict[str, Any] | None = Field(default=None, description="Score/metrics")


class TestScenarioResultResponse(JsonModel):
    """Schema for test scenario result responses."""

    model_config = ConfigDict(from_attributes=True)

    id: TestScenarioResultId
    test_scenario_id: TestScenarioId
    agent_version_id: AgentVersionId
    total_execution_sessions: int
    successful_sessions: int
    failed_sessions: int
    total_execution_time_ms: int
    average_iterations_per_session: int
    total_validation_attempts: int
    final_outcome: dict[str, Any] | None
    score: dict[str, Any] | None
    created_at: datetime
    completed_at: datetime | None
    execution_sessions: list[AgentExecutionSessionResponse] | None = Field(default=None, description="Execution sessions if loaded")


# Query Filter Schemas
class ExecutionSessionFilter(BaseModel):
    """Filter parameters for querying execution sessions."""

    agent_version_id: AgentVersionId | None = Field(default=None, description="Filter by agent version")
    game_id: GameId | None = Field(default=None, description="Filter by game ID")
    test_scenario_id: TestScenarioId | None = Field(default=None, description="Filter by test scenario")
    execution_type: str | None = Field(default=None, description="Filter by execution type")
    move_number_min: int | None = Field(default=None, description="Minimum move number")
    move_number_max: int | None = Field(default=None, description="Maximum move number")
    success_only: bool = Field(False, description="Only show successful executions")


class GameIterationSummary(JsonModel):
    """Summary of iterations for a game, grouped by moves."""

    game_id: GameId
    agent_version_id: AgentVersionId
    total_moves: int
    total_iterations: int
    moves: list[AgentExecutionSessionResponse]  # Ordered by move_number


class AgentVersionIterationSummary(JsonModel):
    """Summary of all iterations for an agent version."""

    agent_version_id: AgentVersionId
    total_games: int
    total_test_scenarios: int
    total_manual_tests: int
    total_execution_sessions: int
    total_iterations: int
    average_iterations_per_move: float
    success_rate: float


# Agent Statistics Update Schema
class AgentStatisticsUpdate(BaseModel):
    """Schema for updating agent statistics (game/environment agnostic)."""

    games_played: int | None = Field(default=None, description="Total number of games played")
    total_winnings: float | None = Field(default=None, description="Total winnings across all games")
    total_losses: float | None = Field(default=None, description="Total losses across all games")
    net_balance: float | None = Field(default=None, description="Current net balance (winnings - losses)")
    win_rate: float | None = Field(default=None, description="Win rate percentage")
    games_won: int | None = Field(default=None, description="Number of games won")
    games_lost: int | None = Field(default=None, description="Number of games lost")
    session_time_seconds: int | None = Field(default=None, description="Total session time in seconds")
    environment_specific_data: dict[str, Any] | None = Field(default=None, description="Environment-specific metrics")
    custom_metrics: dict[str, float] | None = Field(default=None, description="Custom metrics")
    # Additional fields can be added as needed


# Agent Test Schemas for the new test mechanism
class ToolCallRequest(BaseModel):
    """Tool call request from agent during testing."""

    tool_id: ToolId | None = Field(default=None, description="ID of the tool to call")
    tool_name: str = Field(..., description="Name of the tool to call")
    parameters: ToolCallParameters = Field(..., description="Parameters for the tool call")


class ToolCallResponse(JsonModel):
    """Tool execution response."""

    success: bool = Field(..., description="Whether the tool call was successful")
    output: str = Field(..., description="String output from the tool")
    data: BaseModel | None = Field(default=None, description="Structured data returned by the tool")
    error: str | None = Field(default=None, description="Error message if the tool call failed")
    execution_time_ms: int = Field(..., description="Time taken to execute the tool in milliseconds")


class AgentTestRequest(BaseModel):
    """Request for testing an agent with environment-specific input."""

    game_state: dict[str, Any] = Field(..., description="Game state JSON from UI")
    llm_integration_id: LLMIntegrationId = Field(..., description="LLM to use for this test")
    tool_result: ToolCallResponse | None = Field(default=None, description="Result from previous tool execution if continuing")
    iteration_history: list[AgentIterationHistoryEntry] = Field(default_factory=list, description="Previous iterations data")
    max_iterations: int = Field(default=10, ge=1, le=50, description="Maximum iterations allowed from UI")
    max_retries: int = Field(default=3, ge=1, le=10, description="Maximum retries for parsing failures")


class AgentTestResponse(JsonModel):
    """Response from agent test execution."""

    reasoning: AgentReasoning = Field(..., description="Agent's reasoning for the decision")
    action: BaseModel | None = Field(default=None, description="Final action if decided (TexasHoldemMove)")
    tool_request: ToolCallRequest | None = Field(default=None, description="Tool call request if agent needs a tool")
    validation_errors: list[str] = Field(default_factory=list, description="Validation errors if any")
    execution_time_ms: int = Field(..., description="Time taken for this iteration in milliseconds")
    model_used: str = Field(..., description="LLM model used for this iteration")
    is_final: bool = Field(..., description="Whether this is a final decision")
    input_tokens: int | None = Field(default=None, description="Input tokens used")
    output_tokens: int | None = Field(default=None, description="Output tokens generated")
    total_tokens: int | None = Field(default=None, description="Total tokens used")
    cost_usd: float | None = Field(default=None, description="Cost in USD for this iteration")

    @model_serializer
    def serialize_model(self) -> dict[str, Any]:
        """Custom serializer to properly handle the action field."""
        data = {
            "reasoning": self.reasoning,
            "action": self.action.model_dump() if self.action else None,
            "tool_request": self.tool_request,
            "validation_errors": self.validation_errors,
            "execution_time_ms": self.execution_time_ms,
            "model_used": self.model_used,
            "is_final": self.is_final,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "cost_usd": self.cost_usd,
        }
        return data


class GenerateTestJsonResponse(JsonModel):
    """Response with generated test JSON for an agent."""

    test_input: BaseModel = Field(..., description="Generated test input (TexasHoldemAgentInput)")
    description: str = Field(..., description="Description of the generated test scenario")
    environment: str = Field(..., description="Game environment for this test")


class AgentFullDetailsResponse(AgentResponse):
    """Agent response with full details including active version and tools."""

    active_version: AgentVersionResponse | None = Field(default=None, description="Active agent version with tools")
    total_versions: int = Field(0, description="Total number of versions for this agent")


class GameEnvironmentInfo(JsonModel):
    """Information about a game environment."""

    id: str = Field(..., description="Environment identifier")
    metadata: dict[str, Any] = Field(..., description="Environment metadata")


class GameEnvironmentSchema(JsonModel):
    """Schema information for a game environment."""

    environment: str = Field(..., description="Environment identifier")
    input_schema: dict[str, Any] = Field(..., description="Input schema for the environment")
    output_schema: dict[str, Any] = Field(..., description="Output schema for the environment")
    variables: dict[str, dict[str, Any]] = Field(..., description="Available template variables")


class AutocompleteItem(JsonModel):
    """Autocomplete suggestion item."""

    path: str = Field(..., description="Variable path")
    type: str = Field(..., description="Variable type")
    description: str = Field(..., description="Variable description")
    example: str | int | float | bool | None = Field(default=None, description="Example value")


class PromptValidationResult(JsonModel):
    """Result of prompt validation."""

    valid: bool = Field(..., description="Whether the prompt is valid")
    errors: list[str] = Field(default_factory=list, description="Validation errors")
    variable_references: list[str] = Field(default_factory=list, description="Variables referenced in prompt")
    warnings: list[str] = Field(default_factory=list, description="Validation warnings")


class TestDataGenerationResult(JsonModel):
    """Result of test data generation."""

    game_state: dict[str, Any] = Field(..., description="Generated game state")
    description: str = Field(..., description="Description of the generated scenario")


class AgentTestJsonResult[T: BaseModel](BaseModel):
    """Result of agent test JSON generation."""

    test_input: T = Field(..., description="Generated test input")
    description: str = Field(..., description="Description of the test scenario")
    environment: GameType = Field(..., description="Game environment")


class StateGenerationRequest(BaseModel):
    """Request for generating a game state using LLM."""

    description: str = Field(..., min_length=1, max_length=2000, description="User description of the desired game state")
    llm_integration_id: LLMIntegrationId = Field(..., description="LLM integration to use for generation")


class StateGenerationResponse(JsonModel):
    """Response containing generated game state."""

    state: dict[str, Any] = Field(..., description="Generated and validated game state")
    description: str = Field(..., description="Description of the generated state scenario")
    environment: GameType = Field(..., description="Game environment for this state")
    generation_time_ms: int = Field(..., description="Time taken to generate the state in milliseconds")
    model_used: str = Field(..., description="LLM model used for generation")
    input_tokens: int | None = Field(default=None, description="Input tokens used")
    output_tokens: int | None = Field(default=None, description="Output tokens generated")
    total_tokens: int | None = Field(default=None, description="Total tokens used")
    cost_usd: float | None = Field(default=None, description="Cost in USD for this generation")



class AgentIdLookupResponse(JsonModel):
    """Response with parent agent ID for a given agent version."""

    agent_id: AgentId = Field(..., description="Parent agent ID")


class StateGenerationExamplesResponse(JsonModel):
    """Response containing state generation example prompts."""

    examples: list[str] = Field(default_factory=list, description="Example prompts for state chat")

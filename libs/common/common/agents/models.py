"""Pydantic models for tool creation agent."""

from typing import Any, Generic, TypeVar

from game_api import GameType
from pydantic import Field

from common.utils import JsonModel
from shared_db.models.llm_enums import LLMModelType
from shared_db.models.tool import ToolValidationStatus

# Generic type variables for type-safe tool creation context
TState = TypeVar("TState")
TPossibleMoves = TypeVar("TPossibleMoves")
TMoveData = TypeVar("TMoveData")


class ToolExample(JsonModel):
    """Example tool for an environment."""

    name: str = Field(..., description="Machine name of the tool")
    display_name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="What the tool does")
    code: str = Field(..., description="Complete Python code")
    explanation: str = Field(..., description="Explanation of how it works")


class ToolCreationContext(JsonModel, Generic[TState, TPossibleMoves, TMoveData]):
    """Complete context for tool creation in an environment.

    This is a generic class that can be specialized for any game environment.
    Environment-specific information (constraints, best practices, etc.) comes
    from the environment class itself via get_tool_creation_context() method.
    """

    environment: GameType = Field(..., description="Game environment type")
    state_schema: dict[str, Any] = Field(..., description="JSON Schema for player view state")
    possible_moves_schema: dict[str, Any] = Field(..., description="JSON Schema for possible moves")
    move_data_schema: dict[str, Any] = Field(..., description="JSON Schema for move data")
    constraints: list[str] = Field(default_factory=list, description="Environment-specific constraints")
    best_practices: list[str] = Field(default_factory=list, description="Environment-specific best practices")
    example_tools: list[ToolExample] = Field(default_factory=list, description="Example tools for this environment")
    tool_creation_guidance: str = Field(..., description="Environment-specific guidance for tool creation")


class CodeGenerationResult(JsonModel):
    """Result of code generation."""

    success: bool = Field(..., description="Whether generation succeeded")
    code: str | None = Field(default=None, description="Generated code")
    explanation: str | None = Field(default=None, description="Explanation of the code")
    error: str | None = Field(default=None, description="Error message if failed")


class ValidationResult(JsonModel):
    """Result of validation."""

    is_valid: bool = Field(..., description="Whether validation passed")
    errors: list[str] = Field(default_factory=list, description="Validation errors")
    warnings: list[str] = Field(default_factory=list, description="Validation warnings")
    message: str | None = Field(default=None, description="Success or summary message")


class ImprovementSuggestion(JsonModel):
    """A single improvement suggestion."""

    category: str = Field(..., description="Category of improvement (performance, readability, etc)")
    description: str = Field(..., description="Description of the improvement")
    code_snippet: str | None = Field(default=None, description="Example code showing the improvement")


class ImprovementSuggestions(JsonModel):
    """Suggestions for code improvement."""

    suggestions: list[ImprovementSuggestion] = Field(default_factory=list, description="List of suggestions")
    improved_code: str | None = Field(default=None, description="Fully improved version of the code")


class TestScenarioSuggestion(JsonModel, Generic[TState]):
    """Suggested test scenario.

    Generic over TState to ensure type safety for the game state.
    """

    name: str = Field(..., description="Name of the test scenario")
    description: str = Field(..., description="Description of what is being tested")
    environment: GameType = Field(..., description="Game environment for this test")
    state: TState = Field(..., description="Typed game state for the test")
    expected_behavior: str = Field(..., description="What the tool should do with this state")


class ConversationMessage(JsonModel):
    """A message in the conversation."""

    writer: str = Field(..., description="Who wrote the message: 'human' or 'agent'")
    content: str = Field(..., description="Message content")
    timestamp: str = Field(..., description="ISO timestamp")


class CodeArtifact(JsonModel):
    """Code artifact from agent response."""

    code: str = Field(..., description="The generated code")
    explanation: str | None = Field(default=None, description="Explanation of the code")
    language: str = Field(default="python", description="Programming language")
    validation_status: ToolValidationStatus = Field(
        default=ToolValidationStatus.PENDING,
        description="Validation status of the code",
    )


class TestArtifact(JsonModel, Generic[TState]):
    """Test scenario artifact from agent response.

    Generic over TState to ensure type safety for the game state.
    """

    name: str = Field(..., description="Test scenario name")
    description: str = Field(..., description="Test scenario description")
    environment: GameType = Field(..., description="Game environment for this test")
    state: TState = Field(..., description="Typed game state for the test")
    expected_behavior: str = Field(..., description="Expected behavior")


class AgentResponse(JsonModel, Generic[TState]):
    """Response from the tool creation agent.

    Generic over TState to ensure type safety for test artifacts.
    """

    content: str = Field(..., description="Text response from agent")
    code_artifact: CodeArtifact | None = Field(default=None, description="Code artifact if generated")
    test_artifact: TestArtifact[TState] | None = Field(default=None, description="Test artifact if generated")
    should_summarize: bool = Field(default=False, description="Whether conversation should be summarized")
    model_used: LLMModelType = Field(..., description="Model that generated the response")

"""Game environment schemas for API requests and responses."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from chess_game.chess_api import ChessMoveData, ChessStateView
from game_api import GameType
from pydantic import BaseModel, ConfigDict, Field
from texas_holdem.texas_holdem_api import TexasHoldemMoveData, TexasHoldemPossibleMoves, TexasHoldemStateView

from common.ids import AgentId
from common.types import AgentReasoning


class NotificationType(StrEnum):
    """Types of system notifications that can be sent to agents."""

    GAME_STATE = "game_state"
    TOOL_RESULT = "tool_result"
    ILLEGAL_ACTION = "illegal_action"
    TIMEOUT_WARNING = "timeout_warning"
    GAME_OVER = "game_over"
    VALIDATION_ERROR = "validation_error"
    SYSTEM_ERROR = "system_error"


# Define specific types for better type safety
class ToolCallParameters(BaseModel):
    """Parameters passed to a tool call."""

    model_config = ConfigDict(extra="allow")  # Allow additional fields for different tools

    # This will be extended by specific tool parameter schemas
    # For now, we use a flexible approach but maintain type safety


class ToolCallResult(BaseModel):
    """Result returned by a tool call."""

    success: bool = Field(..., description="Whether the tool call was successful")
    output: str | None = Field(default=None, description="String output from the tool")
    error: str | None = Field(default=None, description="Error message if the tool call failed")
    data: dict[str, str | int | float | bool | None] = Field(default_factory=dict, description="Structured data returned by the tool")


class ToolCall(BaseModel):
    """Represents a tool call made during agent execution."""

    tool_name: str = Field(..., description="Name of the tool called")
    parameters: ToolCallParameters = Field(default_factory=ToolCallParameters, description="Parameters passed to the tool")
    result: ToolCallResult | None = Field(default=None, description="Result returned by the tool")
    execution_time_ms: int | None = Field(default=None, ge=0, description="Time taken to execute the tool")


class AgentIterationEntry(BaseModel):
    """Agent reasoning and action in an iteration."""

    role: str = Field(default="agent", description="Always 'agent'")
    reasoning: AgentReasoning | None = Field(default=None, description="Agent's reasoning for this choice")
    action: dict[str, Any] | None = Field(default=None, description="Action taken by agent (tool call or final move)")
    result: dict[str, Any] | None = Field(default=None, description="Result from tool execution or system feedback")
    validation_errors: list[str] = Field(default_factory=list, description="Validation errors if any")
    tool_result: dict[str, Any] | None = Field(default=None, description="Tool execution result")
    timestamp: int | None = Field(default=None, description="Timestamp")


class SystemNotificationEntry(BaseModel):
    """System notification to the agent."""

    role: str = Field(default="system", description="Always 'system'")
    content: str = Field(..., description="System notification content")
    notification_type: NotificationType = Field(..., description="Type of notification")
    timestamp: int | None = Field(default=None, description="Timestamp")


# Union type for agent iteration history
AgentIterationHistoryEntry = AgentIterationEntry | SystemNotificationEntry


# Agent-specific schemas that extend the game API types
class AgentExecutionContext(BaseModel):
    """Context for agent execution with additional metadata."""

    reasoning: AgentReasoning | None = Field(default=None, description="Agent's reasoning for the action")
    confidence: float | None = Field(default=None, ge=0.0, le=1.0, description="Confidence level in the decision")
    execution_time_ms: int | None = Field(default=None, ge=0, description="Time taken to make the decision")
    tool_calls: list[ToolCall] = Field(default_factory=list, description="Tools called during decision making")


class TexasHoldemAgentInput(BaseModel):
    """Input schema for Texas Hold'em agents."""

    state: TexasHoldemStateView = Field(..., description="Current game state from player's perspective")
    possible_moves: TexasHoldemPossibleMoves | None = Field(default=None, description="Available moves for the agent")
    player_id: AgentId = Field(..., description="ID of the agent/player")
    iteration_history: list[AgentIterationHistoryEntry] = Field(default_factory=list, description="Previous agent iteration history")
    chat_history: list[dict[str, Any]] = Field(default_factory=list, description="Chat messages between agents")


class TexasHoldemAgentOutput(BaseModel):
    """Output schema for Texas Hold'em agents."""

    move: TexasHoldemMoveData = Field(..., description="Move chosen by the agent")
    context: AgentExecutionContext | None = Field(default=None, description="Execution context and metadata")


class ChessAgentInput(BaseModel):
    """Input schema for Chess agents.

    Note: Chess agents must calculate legal moves themselves from the board state.
    No possible_moves list is provided - agents should analyze the position to determine valid moves.
    """

    state: ChessStateView = Field(..., description="Current game state (perfect information)")
    player_id: AgentId = Field(..., description="ID of the agent/player")
    iteration_history: list[AgentIterationHistoryEntry] = Field(default_factory=list, description="Previous agent iteration history")
    chat_history: list[dict[str, Any]] = Field(default_factory=list, description="Chat messages between agents")


class ChessAgentOutput(BaseModel):
    """Output schema for Chess agents."""

    move: ChessMoveData = Field(..., description="Move chosen by the agent")
    context: AgentExecutionContext | None = Field(default=None, description="Execution context and metadata")


# Environment schema registry
ENVIRONMENT_INPUT_SCHEMAS: dict[GameType, type[BaseModel]] = {
    GameType.TEXAS_HOLDEM: TexasHoldemAgentInput,
    GameType.CHESS: ChessAgentInput,
}

ENVIRONMENT_OUTPUT_SCHEMAS: dict[GameType, type[BaseModel]] = {
    GameType.TEXAS_HOLDEM: TexasHoldemAgentOutput,
    GameType.CHESS: ChessAgentOutput,
}


def get_input_schema_for_environment(environment: GameType) -> type[BaseModel]:
    """Get the input schema class for a specific game environment."""
    return ENVIRONMENT_INPUT_SCHEMAS[environment]


def get_output_schema_for_environment(environment: GameType) -> type[BaseModel]:
    """Get the output schema class for a specific game environment."""
    return ENVIRONMENT_OUTPUT_SCHEMAS[environment]


class VariableInfo(BaseModel):
    """Information about a template variable."""

    type: str = Field(..., description="Type of the variable")
    description: str = Field(default="", description="Description of the variable")
    example: str | int | float | bool | None = Field(default=None, description="Example value")


def get_environment_variable_schema(environment: GameType) -> dict[str, VariableInfo]:
    """Get the variable schema for template substitution in a specific environment."""
    input_schema = get_input_schema_for_environment(environment)

    # Generate schema for template variables
    schema = input_schema.model_json_schema()

    # Extract properties that can be used as template variables
    variables: dict[str, VariableInfo] = {}

    def extract_variables(obj: dict[str, Any], prefix: str = "", definitions: dict[str, Any] | None = None) -> None:
        """Recursively extract variables from schema."""
        if definitions is None:
            definitions = schema.get("$defs", {})

        if not isinstance(definitions, dict):
            definitions = {}

        if "properties" in obj:
            for key, value in obj["properties"].items():
                var_path = f"{prefix}.{key}" if prefix else key

                # Add the variable itself if it has a primitive type
                if "type" in value:
                    variables[var_path] = VariableInfo(
                        type=value["type"],
                        description=value.get("description", ""),
                        example=value.get("example"),
                    )

                # Handle anyOf unions (like optional fields: T | None)
                if "anyOf" in value:
                    # Find the non-null option in the union
                    for option in value["anyOf"]:
                        if option.get("type") != "null" and "$ref" in option:
                            ref_path = option["$ref"].split("/")[-1]
                            if ref_path in definitions and isinstance(definitions[ref_path], dict):
                                ref_def = definitions[ref_path]

                                # Check if this is likely an enum
                                if (
                                    "enum" in ref_def
                                    or (ref_def.get("type") == "string" and "enum" in ref_def)
                                    or ref_path in ["BettingRound", "PlayerStatus", "CardRank", "CardSuit", "GameType"]
                                ):
                                    # Treat as enum
                                    variables[var_path] = VariableInfo(
                                        type=f"enum({ref_path})",
                                        description=value.get("description", ""),
                                        example=value.get("example"),
                                    )
                                else:
                                    # Treat as nested object - expand its properties
                                    extract_variables(ref_def, var_path, definitions)
                            break

                # Handle nested objects with $ref (Pydantic model references)
                elif "$ref" in value:
                    ref_path = value["$ref"].split("/")[-1]  # Get the definition name
                    if ref_path in definitions and isinstance(definitions[ref_path], dict):
                        ref_def = definitions[ref_path]

                        # Check if this is likely an enum (has enum property or simple structure)
                        if (
                            "enum" in ref_def
                            or (ref_def.get("type") == "string" and "enum" in ref_def)
                            or ref_path in ["BettingRound", "PlayerStatus", "CardRank", "CardSuit", "GameType"]
                        ):
                            # Treat as enum
                            variables[var_path] = VariableInfo(
                                type=f"enum({ref_path})",
                                description=value.get("description", ""),
                                example=value.get("example"),
                            )
                        else:
                            # Treat as nested object - expand its properties
                            extract_variables(ref_def, var_path, definitions)

                # Handle direct nested objects
                elif value.get("type") == "object" and "properties" in value:
                    extract_variables(value, var_path, definitions)

                # Handle arrays
                elif value.get("type") == "array" and "items" in value:
                    items = value["items"]

                    # Handle array of objects with $ref
                    if "$ref" in items:
                        ref_path = items["$ref"].split("/")[-1]
                        if ref_path in definitions and isinstance(definitions[ref_path], dict):
                            extract_variables(definitions[ref_path], f"{var_path}[0]", definitions)

                    # Handle array of direct objects
                    elif items.get("type") == "object" and "properties" in items:
                        extract_variables(items, f"{var_path}[0]", definitions)

                    # Handle array of primitives
                    elif "type" in items:
                        variables[f"{var_path}[0]"] = VariableInfo(
                            type=items["type"],
                            description=f"Item from {value.get('description', 'array')}",
                            example=items.get("example"),
                        )

        # Handle allOf (inheritance/composition)
        if "allOf" in obj:
            for sub_schema in obj["allOf"]:
                if "$ref" in sub_schema:
                    ref_path = sub_schema["$ref"].split("/")[-1]
                    if ref_path in definitions and isinstance(definitions[ref_path], dict):
                        extract_variables(definitions[ref_path], prefix, definitions)
                elif "properties" in sub_schema:
                    extract_variables(sub_schema, prefix, definitions)

    extract_variables(schema)
    return variables

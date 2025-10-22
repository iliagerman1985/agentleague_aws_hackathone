"""AgentCore API models for communication between AgentCore client and AgentCoreExecutionService."""

from __future__ import annotations

from typing import Any

from game_api import GameType
from pydantic import Field

from common.types import AgentReasoning, ExecutedToolCall
from common.utils.json_model import JsonModel
from shared_db.schemas.agent import AgentVersionResponse
from shared_db.schemas.llm_integration import LLMIntegrationWithKey
from shared_db.schemas.tool import ToolResponse


class Message(JsonModel):
    """Typed representation of a message in the execution context."""

    role: str
    content: str


class AgentCoreInvocationRequest(JsonModel):
    """Request model for invoking an agent through AgentCore.

    All data must be included in the request since AgentCore handler
    cannot access the database - it's a stateless HTTP endpoint.
    """

    agent: AgentVersionResponse  # Full agent data
    tools: list[ToolResponse]  # List of tools available to the agent
    llm_integration: LLMIntegrationWithKey  # LLM integration with API key
    game_type: GameType
    game_state: dict[str, Any]  # dict since it's game-specific
    possible_moves: dict[str, Any] | None = None  # dict since it's game-specific
    execution_context: AgentExecutionContext


class AgentCoreInvocationResponse(JsonModel):
    """Response model for AgentCore agent invocation."""

    result: AgentExecutionResult | None = None
    error: str | None = None
    execution_time_ms: int | None = None


class AgentExecutionResult(JsonModel):
    """Agent execution result."""

    reasoning: AgentReasoning = Field(..., description="Agent's reasoning for the action")
    move_data: dict[str, Any] | None = Field(default=None, description="The move data (game-specific)")  # Must be a dict, don't fucking change it.
    exit: bool = Field(default=False, description="Whether the agent decided to exit the game")
    chat_message: str | None = Field(default=None, description="Message to communicate with other players (required for moves/exits, optional for tool calls)")
    tool_calls: list[ExecutedToolCall] = Field(default_factory=list, description="List of tool calls made during decision making")
    execution_time_ms: int | None = None
    tokens_used: int | None = None
    execution_context: AgentExecutionContext


class AgentExecutionContext(JsonModel):
    """Context for agent execution with retry logic and message history."""

    attempts: int = 0
    max_attempts: int = 10
    messages: list[Message] = Field(default_factory=list)
    failure: str | None = None

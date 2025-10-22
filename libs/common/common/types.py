"""Shared type definitions for the AgentLeague application."""

from typing import Any, NewType

from pydantic import Field

from common.utils.json_model import JsonModel

AgentReasoning = NewType("AgentReasoning", str)


class ExecutedToolCall(JsonModel):
    """Record of a tool call execution during agent decision making."""

    tool_name: str = Field(..., description="Name of the tool that was called")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Parameters passed to the tool")
    result: Any = Field(default=None, description="Result returned by the tool")
    error: str | None = Field(default=None, description="Error message if tool execution failed")

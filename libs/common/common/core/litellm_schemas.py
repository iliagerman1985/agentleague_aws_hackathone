"""LiteLLM schemas for unified LLM provider interface."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal, Protocol

from pydantic import BaseModel, Field

from shared_db.models.llm_enums import LLMModelType


class MessageRole(StrEnum):
    """Message roles for conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class FinishReason(StrEnum):
    """Reasons why a completion finished."""

    STOP = "stop"
    LENGTH = "length"
    CONTENT_FILTER = "content_filter"
    TOOL_CALLS = "tool_calls"
    FUNCTION_CALL = "function_call"


class ToolCallType(StrEnum):
    """Types of tool calls."""

    FUNCTION = "function"


class ToolParameterProperty(BaseModel):
    """Property definition for tool parameters."""

    type: str = Field(..., description="Parameter type (string, number, boolean, etc.)")
    description: str = Field(..., description="Description of the parameter")
    enum: list[str] | None = Field(default=None, description="Allowed values for enum parameters")
    items: "ToolParameterProperty | None" = Field(default=None, description="Items type for array parameters")
    properties: dict[str, "ToolParameterProperty"] | None = Field(default=None, description="Properties for object parameters")
    required: list[str] | None = Field(default=None, description="Required properties for object parameters")


class ToolParameters(BaseModel):
    """Parameters schema for tool definitions."""

    type: Literal["object"] = Field(default="object", description="Parameters type (always object)")
    properties: dict[str, ToolParameterProperty] = Field(..., description="Parameter properties")
    required: list[str] = Field(default_factory=list, description="Required parameter names")


class ToolDefinition(BaseModel):
    """Definition of a tool for the LLM."""

    name: str = Field(..., description="Name of the tool")
    description: str = Field(..., description="Description of the tool")
    parameters: ToolParameters = Field(..., description="Parameters schema for the tool")


class FunctionCall(BaseModel):
    """Function call details from tool response."""

    name: str = Field(..., description="Function name")
    arguments: str = Field(..., description="Function arguments as JSON string")


class ToolCallResponse(BaseModel):
    """Response containing tool calls from the LLM."""

    id: str = Field(..., description="Tool call ID")
    type: ToolCallType = Field(default=ToolCallType.FUNCTION, description="Type of tool call")
    function: FunctionCall = Field(..., description="Function call details")


@dataclass
class ChatMessage:
    """Chat message for LiteLLM conversations."""

    role: MessageRole
    content: str


@dataclass
class LiteLLMConfig:
    """Configuration for LiteLLM requests."""

    max_tokens: int | None = None
    temperature: float | None = None
    top_p: float | None = None
    stream: bool = False
    tools: list[ToolDefinition] | None = None
    tool_choice: str | None = None


class TokenUsage(BaseModel):
    """Token usage information from LLM response."""

    prompt_tokens: int = Field(0, description="Number of tokens in the prompt")
    completion_tokens: int = Field(0, description="Number of tokens in the completion")
    total_tokens: int = Field(0, description="Total number of tokens used")


class LiteLLMResponse[T](BaseModel):
    """Response from LiteLLM completion."""

    content: T | None = Field(None, description="Response content (can be None if LLM returns empty)")
    tool_calls: list[ToolCallResponse] | None = Field(default=None, description="Tool calls extracted from the response, if any")
    model: LLMModelType = Field(..., description="Model used for completion")
    finish_reason: FinishReason | None = Field(default=None, description="Reason completion finished")
    usage: TokenUsage | None = Field(default=None, description="Token usage information")
    cost_usd: float | None = Field(default=None, description="Cost in USD for this completion")


# Protocols for third-party library types
class LiteLLMFunctionProtocol(Protocol):
    """Protocol for LiteLLM function objects."""

    name: str
    arguments: str

    def model_dump(self) -> dict[str, str]:
        """Convert to dictionary format."""
        ...


class LiteLLMToolCallProtocol(Protocol):
    """Protocol for LiteLLM tool call objects."""

    id: str
    type: str
    function: LiteLLMFunctionProtocol


class LiteLLMMessageProtocol(Protocol):
    """Protocol for LiteLLM message objects."""

    content: str | None
    tool_calls: list[LiteLLMToolCallProtocol] | None


class LiteLLMChoiceProtocol(Protocol):
    """Protocol for LiteLLM choice objects."""

    message: LiteLLMMessageProtocol
    finish_reason: str


class LiteLLMUsageProtocol(Protocol):
    """Protocol for LiteLLM usage objects."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class LiteLLMResponseProtocol(Protocol):
    """Protocol for LiteLLM response objects."""

    choices: list[LiteLLMChoiceProtocol]
    model: LLMModelType
    usage: LiteLLMUsageProtocol | None


class LiteLLMDeltaProtocol(Protocol):
    """Protocol for LiteLLM streaming delta objects."""

    content: str | None


class LiteLLMStreamChoiceProtocol(Protocol):
    """Protocol for LiteLLM streaming choice objects."""

    delta: LiteLLMDeltaProtocol


class LiteLLMStreamChunkProtocol(Protocol):
    """Protocol for LiteLLM streaming chunk objects."""

    choices: list[LiteLLMStreamChoiceProtocol]


class StreamingResponseProtocol(Protocol):
    """Protocol for streaming response iterator."""

    def __aiter__(self) -> "StreamingResponseProtocol": ...
    def __anext__(self) -> LiteLLMStreamChunkProtocol: ...


class GoogleResponseProtocol(Protocol):
    """Protocol for Google GenerativeAI response."""

    text: str | None

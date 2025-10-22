"""Schemas for tool creation agent API."""

from typing import Any, Literal

from game_api import GameType
from pydantic import BaseModel, Field

from common.agents.models import CodeArtifact, ConversationMessage, TestArtifact
from common.ids import LLMIntegrationId
from common.utils.json_model import JsonModel
from shared_db.models.llm_enums import LLMModelType


class ToolAgentChatRequest(BaseModel):
    """Request for tool creation agent chat."""

    message: str = Field(..., description="User message")
    conversation_history: list[ConversationMessage] = Field(
        default_factory=list,
        description="Previous conversation messages (typed)",
    )
    integration_id: LLMIntegrationId = Field(..., description="LLM integration ID")
    model_id: LLMModelType | None = Field(default=None, description="Specific model to use (optional)")
    environment: GameType = Field(..., description="Game environment for context (required)")
    current_tool_code: str | None = Field(default=None, description="Current tool code in editor")


class ToolAgentChatResponse(JsonModel):
    """Response from tool creation agent."""

    content: str = Field(..., description="Agent response text")
    code_artifact: CodeArtifact | None = Field(default=None, description="Code artifact if generated")
    test_artifact: TestArtifact[Any] | None = Field(default=None, description="Test artifact if generated")
    model_used: LLMModelType = Field(..., description="Model that generated the response")
    should_summarize: bool = Field(default=False, description="Whether conversation should be summarize")


class ToolAgentStreamChunk(JsonModel):
    """Streaming chunk for tool creation agent response."""

    type: Literal["content", "tool", "test", "done", "error"] = Field(..., description="Chunk type")
    content: str | None = Field(default=None, description="Text content chunk")
    tool_artifact: CodeArtifact | None = Field(default=None, description="Tool code artifact when complete")
    test_artifact: TestArtifact[Any] | None = Field(default=None, description="Test artifact when complete")
    is_complete: bool = Field(default=False, description="Whether response is complete")
    should_summarize: bool = Field(default=False, description="Whether to summarize conversation")
    error: str | None = Field(default=None, description="Error message if type='error'")

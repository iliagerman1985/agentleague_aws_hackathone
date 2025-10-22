"""State Chat schemas for streaming state generation/editing conversations."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from common.ids import LLMIntegrationId
from common.utils.json_model import JsonModel


class StateChatMessage(BaseModel):
    """Individual message in the state chat conversation."""

    writer: Literal["human", "llm"] = Field(..., description="Who wrote the message")
    content: str = Field(..., description="Text content of the message")


class StateChatRequest(BaseModel):
    """Request for streaming state chat generation/editing."""

    message: str = Field(..., description="New user message for this turn")
    conversation_history: list[StateChatMessage] = Field(default_factory=list, description="Prior chat history")
    llm_integration_id: LLMIntegrationId = Field(..., description="LLM integration to use")
    model_id: str | None = Field(default=None, description="Specific model ID to use (overrides integration's default model)")
    current_state: dict[str, Any] | None = Field(default=None, description="Existing player-view state to edit; None to generate new")


class StateChatFinalPayload(JsonModel):
    """Final structured payload returned at the end of a streamed turn."""

    state: dict[str, Any] = Field(..., description="Validated player-view state JSON")
    description: str = Field(..., description="LLM-rewritten human description of state")
    message: str = Field(..., description="Assistant's message for the user")


class StateChatStreamChunk(JsonModel):
    """Streaming chunk for state chat response (NDJSON frames)."""

    type: Literal["content", "done", "error"] = Field(..., description="Chunk type")
    content: str | None = Field(default=None, description="Assistant token/content chunk for chat bubble")
    final: StateChatFinalPayload | None = Field(default=None, description="Final payload when type='done'")
    is_complete: bool = Field(default=False, description="Whether response is complete")
    error: str | None = Field(default=None, description="Error details when type='error'")

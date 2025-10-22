"""Schemas for reporting tool usage by agents (shared_db layer)."""

from pydantic import Field

from common.ids import AgentId
from common.utils.json_model import JsonModel


class AgentSummary(JsonModel):
    """Compact info about an agent that references a tool."""

    id: AgentId = Field(..., description="Agent ID")
    name: str = Field(..., description="Agent name")


class ToolUsageResponse(JsonModel):
    """Response listing agents using a given tool."""

    agents: list[AgentSummary] = Field(default_factory=list, description="Agents that use the tool")
    agents_count: int = Field(0, description="Number of agents using the tool")

"""Pydantic schemas for LLM usage tracking."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from common.ids import AgentVersionId, GameId, LLMUsageId, TestScenarioId, ToolId, UserId
from common.utils.json_model import JsonModel
from shared_db.models.llm_enums import LLMUsageScenario


class LLMUsageCreate(BaseModel):
    """Schema for creating a new LLM usage record."""

    user_id: UserId = Field(..., description="User who triggered this LLM usage")
    agent_version_id: AgentVersionId | None = Field(default=None, description="Optional agent version (for agent moves)")
    scenario: LLMUsageScenario = Field(..., description="Type of LLM usage")
    model_used: str = Field(..., description="LLM model identifier")
    cost_usd: float = Field(..., description="Cost in USD for this API call")
    input_tokens: int = Field(..., description="Number of tokens in the prompt")
    output_tokens: int = Field(..., description="Number of tokens in the completion")
    total_tokens: int = Field(..., description="Total tokens used")
    execution_time_ms: int = Field(..., description="Time taken to execute the LLM call in milliseconds")
    input_prompt: str = Field(..., description="Full prompt sent to the LLM")
    output_response: str = Field(..., description="Full response received from the LLM")
    game_id: GameId | None = Field(default=None, description="Optional game ID (for agent moves)")
    tool_id: ToolId | None = Field(default=None, description="Optional tool ID (for tool generation)")
    test_scenario_id: TestScenarioId | None = Field(default=None, description="Optional test scenario ID")


class LLMUsageResponse(JsonModel):
    """Schema for LLM usage responses."""

    model_config = ConfigDict(from_attributes=True)

    id: LLMUsageId
    user_id: UserId
    agent_version_id: AgentVersionId | None
    scenario: str
    model_used: str
    cost_usd: float
    input_tokens: int
    output_tokens: int
    total_tokens: int
    execution_time_ms: int
    input_prompt: str
    output_response: str
    game_id: GameId | None
    tool_id: ToolId | None
    test_scenario_id: TestScenarioId | None
    created_at: datetime


class LLMUsageSummary(JsonModel):
    """Summary of LLM usage without full prompts (for list views)."""

    model_config = ConfigDict(from_attributes=True)

    id: LLMUsageId
    user_id: UserId
    agent_version_id: AgentVersionId | None
    scenario: str
    model_used: str
    cost_usd: float
    total_tokens: int
    execution_time_ms: int
    game_id: GameId | None
    tool_id: ToolId | None
    test_scenario_id: TestScenarioId | None
    created_at: datetime


class LLMUsageStats(JsonModel):
    """Aggregated statistics for LLM usage."""

    total_calls: int = Field(default=0, description="Total number of LLM API calls")
    total_cost_usd: float = Field(default=0.0, description="Total cost in USD")
    total_tokens: int = Field(default=0, description="Total tokens used")
    total_input_tokens: int = Field(default=0, description="Total input tokens")
    total_output_tokens: int = Field(default=0, description="Total output tokens")
    average_cost_per_call: float = Field(default=0.0, description="Average cost per API call")
    average_tokens_per_call: float = Field(default=0.0, description="Average tokens per API call")
    average_execution_time_ms: float = Field(default=0.0, description="Average execution time in milliseconds")


class LLMUsageByScenario(JsonModel):
    """LLM usage statistics broken down by scenario."""

    scenario: LLMUsageScenario
    stats: LLMUsageStats


class LLMUsageByModel(JsonModel):
    """LLM usage statistics broken down by model."""

    model_used: str
    stats: LLMUsageStats


class LLMUsageCostSummary(JsonModel):
    """Cost summary for a user or agent over a time period."""

    user_id: UserId | None = Field(default=None, description="User ID (if filtering by user)")
    agent_version_id: AgentVersionId | None = Field(default=None, description="Agent version ID (if filtering by agent)")
    start_date: datetime | None = Field(default=None, description="Start of time period")
    end_date: datetime | None = Field(default=None, description="End of time period")
    overall_stats: LLMUsageStats = Field(..., description="Overall statistics")
    by_scenario: list[LLMUsageByScenario] = Field(default_factory=list, description="Statistics by scenario")
    by_model: list[LLMUsageByModel] = Field(default_factory=list, description="Statistics by model")


class AgentLLMCostSummary(JsonModel):
    """Simplified cost summary for agent statistics display."""

    total_cost: float = Field(default=0.0, description="Total cost in USD")
    total_calls: int = Field(default=0, description="Total number of LLM API calls")
    total_tokens: int = Field(default=0, description="Total tokens used")
    avg_cost_per_call: float = Field(default=0.0, description="Average cost per API call")
    avg_execution_time_ms: float = Field(default=0.0, description="Average execution time in milliseconds")
    by_scenario: list[dict[str, Any]] = Field(default_factory=list, description="Statistics by scenario")


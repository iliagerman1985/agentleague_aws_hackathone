"""AgentRunner interface and implementations for different agent execution strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod

from api.agentcore_api import AgentExecutionContext, AgentExecutionResult
from game_api import BaseGameStateView, BasePlayerPossibleMoves, GameType

from shared_db.schemas.agent import AgentVersionResponse
from shared_db.schemas.llm_integration import LLMIntegrationWithKey
from shared_db.schemas.tool import ToolResponse


class AgentRunner(ABC):
    """Abstract base class for agent execution strategies."""

    @abstractmethod
    async def invoke_agent(
        self,
        agent: AgentVersionResponse,
        tools: list[ToolResponse],
        llm_integration: LLMIntegrationWithKey,
        game_type: GameType,
        game_state: BaseGameStateView,
        possible_moves: BasePlayerPossibleMoves | None,
        execution_context: AgentExecutionContext,
        max_retries: int = 3,
        timeout_seconds: int = 300,
    ) -> tuple[AgentExecutionResult, AgentExecutionContext]:
        """Invoke an agent and return the result. All data is provided by the caller, AgentRunner is stateless.

        Args:
            agent: Agent version data
            tools: List of tools available to the agent
            llm_integration: LLM integration with API key
            game_type: Type of game
            game_state: Current game state view
            possible_moves: Possible moves for the agent
            requesting_user_id: User ID of the user who created the game
            execution_context: Execution context for retry logic
            max_retries: Maximum number of retries
            timeout_seconds: Timeout in seconds

        Returns:
            Tuple of (AgentExecutionResult with move data and reasoning, updated AgentExecutionContext)
        """

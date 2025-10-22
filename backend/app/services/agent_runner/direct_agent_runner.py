"""Direct agent runner that calls the execution service directly without HTTP."""

from __future__ import annotations

from typing import override

from api.agentcore_api import AgentExecutionContext, AgentExecutionResult
from game_api import BaseGameStateView, BasePlayerPossibleMoves, GameType

from app.services.agent_execution_service import AgentExecutionService
from app.services.agent_runner import AgentRunner
from app.services.game_env_registry import GameEnvRegistry
from common.utils.utils import get_logger
from shared_db.schemas.agent import AgentVersionResponse
from shared_db.schemas.llm_integration import LLMIntegrationWithKey
from shared_db.schemas.tool import ToolResponse

logger = get_logger()


class DirectAgentRunner(AgentRunner):
    """Direct agent runner that calls the execution service directly without HTTP."""

    def __init__(self, agent_execution_service: AgentExecutionService) -> None:
        self._agent_execution_service = agent_execution_service

    @override
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
        """Invoke agent directly through the execution service.

        All data is provided by the caller.

        Args:
            agent: Agent version data (fetched by GameManager)
            tools: List of tools available to the agent (fetched by GameManager)
            llm_integration: LLM integration with API key (fetched by GameManager)
            game_type: Type of game
            game_state: Current game state view
            possible_moves: Possible moves for the agent
            requesting_user_id: User ID of the user who created the game
            execution_context: Execution context for retry logic
            max_retries: Maximum number of retries (not used in direct execution)
            timeout_seconds: Timeout in seconds (not used in direct execution)

        Returns:
            Tuple of (AgentExecutionResult with move data and reasoning, updated AgentExecutionContext)
        """
        logger.info(f"DirectAgentRunner: Invoking agent {agent.id}")

        # Get game environment types
        registry = GameEnvRegistry.instance()
        env_types = registry.get(game_type).types()

        # Call the execution service directly
        result = await self._agent_execution_service.execute(
            context=execution_context,
            agent=agent,
            types=env_types,
            state_view=game_state,
            possible_moves=possible_moves,
            llm_integration=llm_integration,
            tools=tools,
        )

        # Return the result as AgentExecutionResult (API version)
        api_result = AgentExecutionResult(
            move_data=result.move_data,
            exit=result.exit,
            reasoning=result.reasoning,
            chat_message=result.chat_message,
            tool_calls=result.tool_calls,
            execution_time_ms=None,
            tokens_used=None,
            execution_context=execution_context,
        )

        return api_result, execution_context

"""AgentCore client for local testing with custom endpoint URL."""

from __future__ import annotations

import asyncio
from typing import override
from urllib.parse import urljoin

import aiohttp
from api.agentcore_api import AgentCoreInvocationRequest, AgentCoreInvocationResponse, AgentExecutionContext, AgentExecutionResult
from game_api import BaseGameStateView, BasePlayerPossibleMoves, GameType

from app.services.agent_runner import AgentRunner
from common.core.config_service import ConfigService
from common.utils.utils import get_logger
from shared_db.schemas.agent import AgentVersionResponse
from shared_db.schemas.llm_integration import LLMIntegrationWithKey
from shared_db.schemas.tool import ToolResponse

logger = get_logger()


class LocalHostAgentCoreClient(AgentRunner):
    """AgentCore client for local testing with custom endpoint URL.

    All data is provided by the caller (GameManager) - no database access.
    Sends all data over HTTP to the local AgentCore server.
    """

    def __init__(self, config_service: ConfigService) -> None:
        self.endpoint_url = config_service.get("agentcore.endpoint_url")

        if not self.endpoint_url:
            raise ValueError("AGENTCORE_ENDPOINT_URL must be configured for LocalHostAgentCoreClient")

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
        """Invoke agent through local AgentCore service via HTTP.

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
            max_retries: Maximum number of retries
            timeout_seconds: Timeout in seconds

        Returns:
            Tuple of (AgentExecutionResult with move data and reasoning, updated AgentExecutionContext)
        """
        logger.info(f"LocalHostAgentCoreClient: Invoking agent {agent.id}")

        request = AgentCoreInvocationRequest(
            agent=agent,
            tools=tools,
            llm_integration=llm_integration,
            game_type=game_type,
            game_state=game_state.to_dict(mode="json"),
            possible_moves=possible_moves.to_dict(mode="json") if possible_moves else None,
            execution_context=execution_context,
        )

        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                result = await self._invoke(request, timeout_seconds)
                logger.info(f"AgentCore invocation successful on attempt {attempt + 1}")
                return result

            except Exception as e:
                last_exception = e
                if attempt < max_retries:
                    wait_time = 2**attempt
                    logger.warning(f"AgentCore invocation failed (retryable): {e}, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                    continue
                break

        # All retries exhausted
        logger.error(f"AgentCore invocation failed after {max_retries + 1} attempts")
        raise last_exception or RuntimeError("AgentCore invocation failed")

    async def _invoke(self, request: AgentCoreInvocationRequest, timeout_seconds: int) -> tuple[AgentExecutionResult, AgentExecutionContext]:
        """Invoke agent via custom HTTP endpoint (e.g., localhost)."""
        # Parse the custom endpoint URL
        endpoint_url = self.endpoint_url.rstrip("/")
        invoke_url = urljoin(endpoint_url + "/", "invocations")

        # Configure timeout
        timeout = aiohttp.ClientTimeout(total=timeout_seconds)

        async with (
            aiohttp.ClientSession(timeout=timeout) as session,
            session.post(invoke_url, json=request.to_json(), headers={"Content-Type": "application/json"}) as response,
        ):
            if response.status != 200:
                error_text = await response.text()
                raise RuntimeError(f"HTTP {response.status}: {error_text}")

            response_data = AgentCoreInvocationResponse.model_validate_json(await response.text())

            if response_data.result:
                return response_data.result, response_data.result.execution_context
            else:
                raise RuntimeError(f"Agent execution failed: {response_data.error}")

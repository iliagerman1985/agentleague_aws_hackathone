"""Production AgentCore client that uses AWS AgentCore service."""

from __future__ import annotations

import asyncio
from typing import override

from aiobotocore.config import AioConfig
from aiobotocore.session import get_session
from api.agentcore_api import AgentCoreInvocationRequest, AgentCoreInvocationResponse, AgentExecutionContext, AgentExecutionResult
from botocore.exceptions import ClientError
from game_api import BaseGameStateView, BasePlayerPossibleMoves, GameType

from app.services.agent_runner import AgentRunner
from common.core.config_service import ConfigService
from common.utils.utils import get_logger
from shared_db.schemas.agent import AgentVersionResponse
from shared_db.schemas.llm_integration import LLMIntegrationWithKey
from shared_db.schemas.tool import ToolResponse

logger = get_logger()


class AgentCoreClient(AgentRunner):
    """Production AgentCore client that uses AWS AgentCore service."""

    def __init__(self, config_service: ConfigService) -> None:
        self.runtime_arn = config_service.get("agentcore.runtime_arn")
        self.region = config_service.get("aws.region", "us-east-1")

        if not self.runtime_arn:
            raise ValueError("AGENTCORE_RUNTIME_ARN must be configured for AgentCoreClient")

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
        """Invoke agent through AWS Bedrock AgentCore service.

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
        logger.info(f"AgentCoreClient: Invoking agent {agent.id}")

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

            except ClientError as e:
                last_exception = e
                error_code = e.response.get("Error", {}).get("Code", "Unknown")

                if error_code in ["ThrottlingException", "ServiceUnavailable", "InternalServerException"] and attempt < max_retries:
                    wait_time = 2**attempt  # Exponential backoff
                    logger.warning(f"AgentCore invocation failed (retryable): {error_code}, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                    continue

                logger.exception("AWS AgentCore invocation failed")
                break

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
        """Invoke agent via AWS AgentCore service."""
        session = get_session()

        # Configure aiobotocore for timeout
        config = AioConfig(
            read_timeout=timeout_seconds,
            connect_timeout=30,
            retries={"max_attempts": 0},  # We handle retries ourselves
        )

        async with session.create_client(  # type: ignore
            "bedrock-agentcore", region_name=self.region, config=config
        ) as client:
            response = await client.invoke_agent_runtime(agentRuntimeArn=self.runtime_arn, payload=request.to_json(), qualifier="DEFAULT")
            response_data = AgentCoreInvocationResponse.model_validate_json(await response["response"].read())
            if response_data.result:
                return response_data.result, response_data.result.execution_context
            else:
                raise RuntimeError(f"Agent execution failed: {response_data.error}")

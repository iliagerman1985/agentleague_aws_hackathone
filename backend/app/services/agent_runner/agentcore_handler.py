"""AgentCore execution service that wraps AgentExecutionService for AWS AgentCore deployment."""

from __future__ import annotations

import asyncio
from typing import Any

from api.agentcore_api import AgentCoreInvocationRequest, AgentCoreInvocationResponse, AgentExecutionResult
from bedrock_agentcore import BedrockAgentCoreApp

from app.services.agent_execution_service import AgentExecutionService
from app.services.game_env_registry import GameEnvRegistry
from common.core.litellm_service import LiteLLMService
from common.utils.utils import get_logger

logger = get_logger()

app = BedrockAgentCoreApp()

litellm_service = LiteLLMService()
agent_execution_service = AgentExecutionService(litellm_service)

registry = GameEnvRegistry.instance()


@app.entrypoint  # type: ignore
async def execute_agent(payload: str | dict[str, Any]) -> dict[str, Any]:
    """AgentCore entrypoint for agent execution."""

    try:
        request = AgentCoreInvocationRequest.model_validate_json(payload) if isinstance(payload, str) else AgentCoreInvocationRequest.model_validate(payload)

        # Extract data from request (all data sent over HTTP)
        # Pydantic handles deserialization automatically - these are already typed objects
        agent = request.agent
        tools = request.tools
        llm_integration = request.llm_integration
        game_type = request.game_type
        game_state = request.game_state
        possible_moves = request.possible_moves
        context = request.execution_context

        # Get game environment types
        env_class = registry.get(game_type)
        types = env_class.types()

        # Create state view and possible moves
        state_view = types.player_view_type().model_validate(game_state)
        possible_moves_obj = None
        if possible_moves:
            possible_moves_obj = types.possible_moves_type().model_validate(possible_moves)

        # Execute agent
        start_time = asyncio.get_event_loop().time()
        service_result = await agent_execution_service.execute(
            context=context,
            agent=agent,
            types=types,
            state_view=state_view,
            possible_moves=possible_moves_obj,
            llm_integration=llm_integration,
            tools=tools,
        )
        execution_time_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)

        # Create result object (API version)
        api_result = AgentExecutionResult(
            move_data=service_result.move_data,
            exit=service_result.exit,
            reasoning=service_result.reasoning,
            chat_message=service_result.chat_message,
            tool_calls=service_result.tool_calls,
            execution_time_ms=execution_time_ms,
            tokens_used=None,  # Can be added later if needed
            execution_context=context,
        )

        return AgentCoreInvocationResponse(
            result=api_result,
            execution_time_ms=execution_time_ms,
        ).to_dict(mode="json")

    except Exception as e:
        logger.exception("Error in AgentCore execution")
        error_msg = f"Agent execution failed: {e!s}"

        return AgentCoreInvocationResponse(
            error=error_msg,
        ).to_dict(mode="json")


if __name__ == "__main__":
    app.run()

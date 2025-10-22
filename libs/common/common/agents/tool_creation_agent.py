"""Strands agent configuration for tool creation.

The agent is completely environment-agnostic. All environment-specific information
comes from the ToolCreationContext passed at runtime.
"""

from typing import Any

from strands import Agent
from strands.agent.conversation_manager import SummarizingConversationManager
from strands.models.litellm import LiteLLMModel

from common.agents.models import ToolCreationContext
from common.agents.prompts.tool_creation_prompts import (
    get_summarization_prompt,
    get_system_prompt,
)
from common.agents.tools.code_tools import explain_schema, suggest_improvements, validate_code_syntax
from common.utils.utils import get_logger

logger = get_logger()


def create_tool_creation_agent(
    model: LiteLLMModel,
    context: ToolCreationContext[Any, Any, Any],
) -> Agent:
    """Create a tool creation agent with pure code generation tools.

    This agent is completely environment-agnostic. All environment-specific
    information comes from the context parameter. The agent does NOT interact
    with the database - it only generates and validates code.

    Args:
        model: Strands Model instance for LLM
        context: Tool creation context with environment-specific information

    Returns:
        Configured Strands Agent instance
    """
    # Pure code tools (no database operations)
    all_tools = [
        validate_code_syntax,
        suggest_improvements,
        explain_schema,
    ]

    # Get system prompt with injected schemas and context
    system_prompt = get_system_prompt(context)

    # Create conversation manager with summarization
    conversation_manager = SummarizingConversationManager(
        preserve_recent_messages=10,
        summary_ratio=0.3,
        summarization_system_prompt=get_summarization_prompt(),
    )

    # Create agent
    agent = Agent(
        model=model,
        tools=all_tools,
        system_prompt=system_prompt,
        conversation_manager=conversation_manager,
    )

    logger.info(f"Created tool creation agent for {context.environment.value} with {len(all_tools)} tools")

    return agent

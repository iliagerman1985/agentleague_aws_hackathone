from __future__ import annotations

import json
import re
from typing import Any, cast

from api.agentcore_api import AgentExecutionContext, Message
from game_api import BaseGameStateView, BasePlayerPossibleMoves, GameType, GenericGameEnvTypes, ToolCall
from pydantic import Field

from common.core.app_error import Errors
from common.core.litellm_schemas import ChatMessage, MessageRole
from common.core.litellm_service import LiteLLMService
from common.model_config import ModelConfigFactory
from common.types import AgentReasoning, ExecutedToolCall
from common.utils.json_model import JsonModel
from common.utils.msgspec import encode_json_str
from common.utils.utils import get_logger, is_dict, is_list
from shared_db.models.tool import ToolValidationStatus
from shared_db.schemas.agent import AgentVersionResponse
from shared_db.schemas.llm_integration import LLMIntegrationWithKey, LLMModelType
from shared_db.schemas.tool import ToolResponse

logger = get_logger()


class AgentExecutionResult(JsonModel):
    """Result of agent execution including move, exit decision, and optional chat message."""

    move_data: dict[str, Any] | None = Field(default=None, description="The move chosen by the agent")  # Must be a dict, don't fucking change it.
    exit: bool = Field(default=False, description="Whether the agent decided to exit the game")
    reasoning: AgentReasoning = Field(..., description="Agent's reasoning for the action")
    chat_message: str | None = Field(default=None, description="Message to communicate with other players (required for moves/exits, optional for tool calls)")
    tool_calls: list[ExecutedToolCall] = Field(default_factory=list, description="List of tool calls made during decision making")


class AgentExecutionService:
    """Stateless service for executing agent decisions.

    This service does not maintain any state or database connections.
    All data must be provided via method parameters.
    """

    _litellm_service: LiteLLMService

    def __init__(self, litellm_service: LiteLLMService) -> None:
        self._litellm_service = litellm_service

    async def execute(
        self,
        context: AgentExecutionContext,
        agent: AgentVersionResponse,
        types: type[GenericGameEnvTypes],
        state_view: BaseGameStateView,
        possible_moves: BasePlayerPossibleMoves | None,
        llm_integration: LLMIntegrationWithKey,
        tools: list[ToolResponse],
    ) -> AgentExecutionResult:
        """Execute agent decision with tool call loop.

        Args:
            context: Execution context for retry logic
            agent: Agent version to execute
            types: Game environment types
            state_view: Current game state view
            possible_moves: Possible moves for the agent
            llm_integration: LLM integration to use (already fetched by caller)
            tools: List of validated tools available to the agent (already fetched by caller)
        """

        # Resolve provider and model
        is_fast_mode = False  # (iteration_count > 1) -> use fast LLM after first iteration
        provider = agent.fast_llm_provider if is_fast_mode else agent.slow_llm_provider
        model_override = agent.fast_llm_model if is_fast_mode else agent.slow_llm_model

        if model_override:
            if not ModelConfigFactory.validate_provider_model(provider, model_override):
                raise Errors.Agent.INVALID_OUTPUT.create(f"Invalid model '{model_override}' for provider '{provider}'")
            model_enum: LLMModelType = cast(LLMModelType, model_override)
        else:
            model_enum = llm_integration.selected_model

        # Convert context messages to ChatMessage format for internal use
        chat_messages: list[ChatMessage] = self._convert_to_chat_messages(context.messages)

        # Initialize system prompt if not already set
        if not chat_messages:
            system_prompt = self._prepare_prompt(agent, types, state_view, possible_moves, tools)
            chat_messages = [ChatMessage(role=MessageRole.SYSTEM, content=system_prompt)]

        # Track all tool calls made during this execution
        executed_tool_calls: list[ExecutedToolCall] = []

        while context.attempts < context.max_attempts:
            context.attempts += 1
            logger.info(f"Agent execution attempt {context.attempts}/{context.max_attempts}")

            # Handle previous failure if it exists in context
            if context.failure:
                # Format failure as clear error feedback, not game state
                failure_message = f"SYSTEM FEEDBACK: The previous move attempt failed with error: {context.failure}. Please analyze the error and provide a valid move or tool call."
                chat_messages.append(ChatMessage(role=MessageRole.USER, content=failure_message))
                context.failure = None

            try:
                response = await self._litellm_service.chat_completion(
                    provider=llm_integration.provider,
                    model=model_enum,
                    messages=chat_messages,
                    api_key=llm_integration.api_key,
                    output_type=types.agent_decision_type(),
                )

                # Check if response content is None - log and retry
                if response.content is None:
                    raise Errors.Agent.INVALID_OUTPUT.create("You returned an empty response")

                decision = response.content
                if not decision.reasoning:
                    raise Errors.Agent.INVALID_OUTPUT.create("Reasoning is required for moves")
                chat_messages.append(ChatMessage(role=MessageRole.ASSISTANT, content=decision.to_json()))

                # Log if agent returned multiple actions (should not happen)
                actions = sum(bool(x) for x in [decision.tool_call, decision.move, decision.exit])
                if actions > 1:
                    logger.warning("Agent returned multiple actions - prioritizing in order: exit > tool_call > move")
                    if decision.exit:
                        logger.warning("Agent also returned tool_call or move with exit - ignoring them")
                    elif decision.tool_call and decision.move:
                        logger.warning(f"Agent returned both tool call and move - prioritizing tool call: {decision.tool_call.tool_name}")

                if decision.exit:
                    # Validate that chat_message is provided for exits
                    if not decision.chat_message:
                        raise Errors.Agent.INVALID_OUTPUT.create("Chat message is required when exiting the game")

                    logger.info("Agent decided to exit the game")
                    # Update context with final messages before returning
                    context.messages = self._convert_from_chat_messages(chat_messages)
                    return AgentExecutionResult(
                        exit=True,
                        reasoning=decision.reasoning,
                        chat_message=decision.chat_message,
                        tool_calls=executed_tool_calls,
                    )
                elif decision.tool_call:
                    # Prioritize tool calls over moves for iterative execution
                    tool_result = await self._execute_tool(decision.tool_call, tools, state_view)
                    if tool_result.error:
                        raise Errors.Agent.INVALID_OUTPUT.create(f"Tool call failed: {tool_result.error}")

                    # Track this tool call
                    executed_tool_calls.append(
                        ExecutedToolCall(
                            tool_name=decision.tool_call.tool_name,
                            parameters=decision.tool_call.parameters or {},
                            result=tool_result.result,
                            error=tool_result.error,
                        )
                    )

                    chat_messages.append(
                        ChatMessage(
                            role=MessageRole.USER,
                            content=f"Tool '{decision.tool_call.tool_name}' result: {encode_json_str(tool_result.result)}",
                        )
                    )
                    # Continue loop to ask agent again after tool execution
                elif decision.move:
                    # Validate that chat_message is provided for moves
                    if not decision.chat_message:
                        raise Errors.Agent.INVALID_OUTPUT.create("Chat message is required when making a move")

                    logger.info(f"Agent returned final move: {decision.move}")
                    # Update context with final messages before returning
                    context.messages = self._convert_from_chat_messages(chat_messages)
                    return AgentExecutionResult(
                        move_data=decision.move.to_dict(mode="json"),
                        reasoning=decision.reasoning,
                        chat_message=decision.chat_message,
                        tool_calls=executed_tool_calls,
                    )
                else:
                    raise Errors.Agent.INVALID_OUTPUT.create("Agent must either make a tool call, make a move, or exit the game")

            except Exception as e:
                logger.exception(f"Error in agent execution attempt {context.attempts}")

                # If we've reached max attempts, re-raise the error
                if context.attempts >= context.max_attempts:
                    raise

                context.failure = str(e)

        # Update context with final messages before raising
        context.messages = self._convert_from_chat_messages(chat_messages)
        raise Errors.Agent.MAX_ITERATIONS_EXCEEDED.create()

    def _convert_to_chat_messages(self, messages: list[Message]) -> list[ChatMessage]:
        """Convert API Message objects to ChatMessage objects for LiteLLM."""
        chat_messages: list[ChatMessage] = []
        for msg in messages:
            try:
                role = MessageRole(msg.role)
            except ValueError:
                # Default to USER if role is not recognized
                role = MessageRole.USER
            chat_messages.append(ChatMessage(role=role, content=msg.content))
        return chat_messages

    def _convert_from_chat_messages(self, chat_messages: list[ChatMessage]) -> list[Message]:
        """Convert ChatMessage objects back to API Message objects."""
        return [Message(role=msg.role.value, content=msg.content) for msg in chat_messages]

    def _prepare_prompt(
        self,
        agent: AgentVersionResponse,
        types: type[GenericGameEnvTypes],
        state_view: BaseGameStateView,
        possible_moves: BasePlayerPossibleMoves | None,
        tools: list[ToolResponse],
    ) -> str:
        # Inject prompt sections (tools, output schema, input/output type schemas)
        system_prompt_with_sections = self._inject_prompt_sections(agent=agent, types=types, tools=tools)

        # Extract chat history from events
        chat_history: list[dict[str, Any]] = []
        for event in state_view.events:
            event_dict = event.to_dict(mode="json")
            if event_dict.get("event") == "Chat Message":
                chat_history.append(
                    {
                        "player_id": event_dict.get("player_id"),
                        "message": event_dict.get("message"),
                        "timestamp": event_dict.get("timestamp"),
                    }
                )

        # Apply variable substitution to the FINAL system prompt (including injected sections)
        state_for_prompt = {
            **state_view.to_dict(mode="json"),
            "events": [e.to_dict(mode="json") for e in state_view.events],
            "chatHistory": chat_history,
        }

        state_for_prompt["possibleMoves"] = possible_moves.to_dict(mode="json") if possible_moves else None

        system_prompt = self._substitute_variables(system_prompt_with_sections, state_for_prompt)

        # Inject per-game MOVE SCHEMA, and for Chess also inject POSSIBLE_MOVES_EXAMPLES
        move_schema = types.player_move_type().model_json_schema()
        sections: list[str] = [system_prompt, "\n[MOVE SCHEMA]\n", json.dumps(move_schema, indent=2)]

        # For Chess: provide examples and board indexing documentation
        if types.type() == GameType.CHESS:
            # Add simplified board representation documentation
            board_indexing_doc = """
[CHESS BOARD REPRESENTATION]
You receive the board state as a simple coordinate map where:
- Keys are chess board squares like "a1", "e4", "h8", etc.
- Values are pieces with type and color
- Squares not in the map are empty

Example: {
  "a1": {"type": "rook", "color": "white"},
  "e4": {"type": "pawn", "color": "white"},
  "h8": {"type": "rook", "color": "black"}
}

[CRITICAL: USE PROVIDED LEGAL MOVES]
The state includes a "possibleMoves" field containing ALL legal moves for your pieces.
This list is pre-calculated and guaranteed to be correct according to chess rules.

IMPORTANT RULES:
• You MUST choose a move from the possibleMoves list
• Each move shows: from_square, to_square, piece type, is_check (whether it puts opponent in check), and promotion options (if applicable)
• The possibleMoves list already accounts for:
  - All piece movement rules
  - Check and pins (moves that would leave your king in check are excluded)
  - Castling availability (based on castling_rights)
  - En passant captures (based on en_passant_square)
  - Pawn promotion requirements
• Do NOT attempt to make moves not in the possibleMoves list - they are illegal
• Focus on strategic evaluation and choosing the best move from the legal options

Example possibleMoves format:
{
  "possible_moves": [
    {"from_square": "e2", "to_square": "e4", "piece": "pawn", "is_check": false, "promotion": null},
    {"from_square": "g1", "to_square": "f3", "piece": "knight", "is_check": false, "promotion": null},
    {"from_square": "e7", "to_square": "e8", "piece": "pawn", "is_check": true, "promotion": ["q", "r", "b", "n"]}
  ]
}
"""
            sections.append(board_indexing_doc)

            examples = {
                "examples": [
                    {
                        "label": "normal move",
                        "move": {"from_square": "g1", "to_square": "f3", "promotion": None},
                    },
                    {
                        "label": "promotion (must include promotion; choose one)",
                        "move": {"from_square": "e7", "to_square": "e8", "promotion": "q"},
                        "promotion_options": ["q", "r", "b", "n"],
                    },
                    {
                        "label": "castle kingside",
                        "move": {"from_square": "e1", "to_square": "g1", "promotion": None},
                    },
                    {
                        "label": "castle queenside",
                        "move": {"from_square": "e1", "to_square": "c1", "promotion": None},
                    },
                ]
            }
            sections += ["\n[POSSIBLE_MOVES_EXAMPLES]\n", encode_json_str(examples)]

        # Add conversation instructions if present
        if agent.conversation_instructions:
            sections.append("\n[CONVERSATION INSTRUCTIONS]")
            sections.append(agent.conversation_instructions)
            sections.append("\nYou can communicate with other agents using the 'chat_message' field in your response.")
            sections.append("Use this to share your thoughts, strategies, or coordinate with other players.")

        # Add exit criteria if present
        if agent.exit_criteria:
            sections.append("\n[EXIT CRITERIA]")
            sections.append(agent.exit_criteria)

        return "\n".join(sections)

    def _substitute_variables(self, template: str, player_view_state: dict[str, Any]) -> str:
        def replace_variable(match: re.Match[str]) -> str:
            var_path = match.group(1)

            # Special case: if variable path is exactly "state", return player view state as JSON
            if var_path == "state":
                return json.dumps(player_view_state, indent=2)

            # For all other paths, use the existing player view logic
            value = self._get_nested_value(player_view_state, var_path)
            return str(value) if value is not None else f"${{{var_path}}}"

        # Replace ${{variable.path}} with actual values
        pattern = r"\$\{\{([^}]+)\}\}"
        return re.sub(pattern, replace_variable, template)

    def _get_nested_value(
        self,
        data: dict[str, Any],
        path: str,
    ) -> Any:
        """Get nested value from dictionary using dot notation.

        Args:
            data: Dictionary to search
            path: Dot-separated path (e.g., "player.chips")

        Returns:
            Value at path or None if not found
        """
        keys = path.split(".")
        value = data

        for key in keys:
            # Handle array indexing
            if "[" in key and "]" in key:
                base_key, index_str = key.split("[")
                index = int(index_str.rstrip("]"))

                if is_dict(value) and base_key in value:
                    value = value[base_key]
                    if is_list(value) and 0 <= index < len(value):
                        value = value[index]
                    else:
                        return None
                else:
                    return None
            elif is_dict(value) and key in value:
                value = value[key]
            else:
                return None

        return value

    def _inject_prompt_sections(self, agent: AgentVersionResponse, types: type[GenericGameEnvTypes], tools: list[ToolResponse]) -> str:
        """Inject tools catalog, output schema, and type schemas into the system prompt.

        The final system prompt will include:
        - Core prompt (with substituted variables)
        - Tools catalog: name, description, and parameters (if available)
        - Output JSON schema (AgentDecision)
        - Input and Output type schemas
        """
        sections: list[str] = []
        sections.append(agent.system_prompt)

        # 1) Tools catalog from tool_ids with parameter descriptions
        if tools:
            tool_lines: list[str] = ["Tools you may call:"]
            for tool in tools:
                # Create XML representation of the tool
                tool_lines.append("\n<tool>")
                tool_lines.append(f"  <name>{tool.name}</name>")
                tool_lines.append(f"  <description>{tool.description}</description>")
                tool_lines.append("  <parameters>")
                tool_lines.append("    Check tool documentation for parameter details")
                tool_lines.append("  </parameters>")
                tool_lines.append("</tool>")

            sections.append("\n[TOOLS]\n" + "\n".join(tool_lines))
            sections.append("\n⚠️ CRITICAL: Choose EXACTLY ONE action per response:")
            sections.append("  1. Call a tool (set 'tool_call' field, leave 'move' and 'exit' as null)")
            sections.append("  2. Make a final move (set 'move' field, leave 'tool_call' and 'exit' as null)")
            sections.append("  3. Exit the game (set 'exit' field to true, leave 'tool_call' and 'move' as null)")
            sections.append("• NEVER set multiple action fields in the same response - this will cause errors")
            sections.append("• If you need information before making a move, call a tool first")
            sections.append("• After receiving tool results, make your final move in the next response")
            sections.append("\nREASONING FIELD (REQUIRED - FILL THIS FIRST):")
            sections.append("• The 'reasoning' field explains WHY you chose this specific action")
            sections.append("• If calling a tool: explain why you need this information")
            sections.append("• If making a move: explain your strategic thinking behind this move")
            sections.append("• If exiting: explain why you're leaving the game")
            sections.append("\nCHAT MESSAGE:")
            sections.append("• REQUIRED when making a move or exiting - must provide a message")
            sections.append("• OPTIONAL when calling a tool - can be null")
            sections.append("• The message should reflect your agent's personality and the current situation")
            sections.append("• Keep it concise but engaging - other players will see this message")
            sections.append("\nTOOL USAGE INSTRUCTIONS:")
            sections.append("• To call a tool, use the action field with type='tool', tool_name, and parameters as a JSON object.")
            sections.append(
                "• If the tool has parameters, ALWAYS provide required parameters - check tool requirements carefully! Do NOT send empty parameters {}."
            )
        else:
            sections.append("\n[NO TOOLS AVAILABLE]")
            sections.append("You do not have access to any tools for this decision.")
            sections.append("You must make your move directly using the 'move' field in your response.")
            sections.append("Do NOT attempt to call any tools - they will fail and waste iterations.")
            sections.append("\nREASONING FIELD (REQUIRED - FILL THIS FIRST):")
            sections.append("• The 'reasoning' field explains WHY you chose this specific action")
            sections.append("• If making a move: explain your strategic thinking behind this move")
            sections.append("• If exiting: explain why you're leaving the game")
            sections.append("\nCHAT MESSAGE (REQUIRED):")
            sections.append("• You MUST provide a 'chat_message' when making a move or exiting")
            sections.append("• The message should reflect your agent's personality and the current game situation")
            sections.append("• Keep it concise but engaging - other players will see this message")

        # 2) Output JSON schema
        schema = types.agent_decision_type().model_json_schema()
        schema_str = json.dumps(schema, indent=2)
        sections.append(
            f"\n[OUTPUT SCHEMA]\nYou must respond with a JSON object that strictly matches the schema below. No extra commentary outside of JSON.\n{schema_str}"
        )

        return "\n\n".join(sections)

    async def _execute_tool(self, tool_call: ToolCall, available_tools: list[ToolResponse], state_view: BaseGameStateView) -> ToolCallResult:
        """Execute a tool call by running the tool's Python code."""
        try:
            # Find the tool by name from the available tools
            tool = None
            for t in available_tools:
                if t.name == tool_call.tool_name:
                    tool = t
                    break

            if not tool:
                return ToolCallResult(result=None, error=f"Tool '{tool_call.tool_name}' not found")

            if tool.validation_status != ToolValidationStatus.VALID:
                return ToolCallResult(result=None, error=f"Tool '{tool_call.tool_name}' is not validated (status: {tool.validation_status})")

            # Prepare the lambda event structure with context injection
            lambda_event = {"body": {**(tool_call.parameters or {}), "context": {"state": state_view.to_dict(mode="json")}}}

            # Execute the tool code using Python's exec
            # Create a safe execution environment
            exec_globals = {
                "__builtins__": {
                    "__import__": __import__,  # Required for import statements
                    "print": print,
                    "len": len,
                    "str": str,
                    "int": int,
                    "float": float,
                    "bool": bool,
                    "list": list,
                    "dict": dict,
                    "tuple": tuple,
                    "set": set,
                    "range": range,
                    "enumerate": enumerate,
                    "zip": zip,
                    "map": map,
                    "filter": filter,
                    "sorted": sorted,
                    "sum": sum,
                    "min": min,
                    "max": max,
                    "abs": abs,
                    "round": round,
                    "isinstance": isinstance,
                    "hasattr": hasattr,
                    "getattr": getattr,
                    "setattr": setattr,
                    "type": type,
                    "ord": ord,
                    "chr": chr,
                    "ValueError": ValueError,
                    "TypeError": TypeError,
                    "KeyError": KeyError,
                    "IndexError": IndexError,
                    "AttributeError": AttributeError,
                    "Exception": Exception,
                },
                "__name__": "__main__",  # Some modules expect this
            }
            exec_locals: dict[str, Any] = {}

            # Execute the tool code
            exec(tool.code, exec_globals, exec_locals)

            # Call the lambda_handler function
            if "lambda_handler" not in exec_locals:
                return ToolCallResult(result=None, error=f"Tool '{tool_call.tool_name}' does not define a lambda_handler function")

            lambda_handler = exec_locals["lambda_handler"]
            context: dict[str, Any] = {}  # Empty context like in frontend

            # Execute the handler
            result: Any = lambda_handler(lambda_event, context)

            return ToolCallResult(result=result, error=None)

        except Exception as e:
            logger.exception(f"Error executing tool '{tool_call.tool_name}'")
            return ToolCallResult(result=None, error=f"Tool execution failed: {e!s}")


class ToolCallResult(JsonModel):
    """Result from a single tool execution."""

    result: Any | None = None
    error: str | None = None

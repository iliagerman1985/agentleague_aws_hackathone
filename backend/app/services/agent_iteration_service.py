"""Agent iteration service for iteration and message management operations."""

import json
import time
from typing import Any

from common.types import AgentReasoning
from common.utils.utils import get_logger
from shared_db.schemas.game_environments import AgentIterationEntry, AgentIterationHistoryEntry, NotificationType, SystemNotificationEntry

logger = get_logger()


class AgentIterationService:
    """Service layer for agent iteration operations.
    Handles iteration creation, message conversion, and history management.
    """

    def __init__(self) -> None:
        """Initialize AgentIterationService."""

    def iterations_to_messages(self, iterations: list[AgentIterationHistoryEntry], system_prompt: str) -> list[dict[str, str]]:
        """Convert iterations to chat messages for LLM communication.

        Args:
            iterations: List of iteration entries (AgentIterationEntry or SystemNotificationEntry)
            system_prompt: System prompt to include as first message

        Returns:
            List of chat messages with role and content
        """
        messages = [{"role": "system", "content": system_prompt}]

        for iteration in iterations:
            if isinstance(iteration, AgentIterationEntry):
                # Agent responses become assistant messages
                if iteration.reasoning and iteration.action:
                    agent_response = {"reasoning": iteration.reasoning, "action": iteration.action}
                    messages.append({"role": "assistant", "content": json.dumps(agent_response, indent=2)})

                    # If this was a tool call with result, add the tool result as user message
                    if iteration.action.get("type") == "tool" and iteration.tool_result:
                        tool_name = iteration.action.get("tool_name", "unknown")

                        # Check if the tool execution was successful (UI should parse this correctly)
                        tool_success = iteration.tool_result.get("success", True)  # Default to True for backward compatibility

                        if tool_success:
                            messages.append(
                                {"role": "user", "content": f"Tool '{tool_name}' executed successfully. Result:\n{json.dumps(iteration.tool_result, indent=2)}"}
                            )
                        else:
                            # Tool failed - provide error feedback
                            error_msg = iteration.tool_result.get("error", "Unknown error occurred")
                            messages.append(
                                {
                                    "role": "user",
                                    "content": f"Tool '{tool_name}' execution failed. Error: {error_msg}\n\nPlease fix the tool parameters and try again. Check the tool description for correct parameter names and formats.",
                                }
                            )

                    # Add validation errors as user feedback
                    if iteration.validation_errors:
                        error_msg = "Your previous response had validation errors:\n"
                        for error in iteration.validation_errors:
                            error_msg += f"• {error}\n"
                        error_msg += "\nPlease correct these issues in your next response."
                        messages.append({"role": "user", "content": error_msg})

            else:  # SystemNotificationEntry
                # System notifications become user messages
                messages.append({"role": "user", "content": f"System notification ({iteration.notification_type}): {iteration.content}"})

        return messages

    def create_system_notification(self, content: str, notification_type: NotificationType) -> SystemNotificationEntry:
        """Create a system notification iteration entry.

        Args:
            content: Notification content
            notification_type: Type of notification (game_state, tool_result, etc.)

        Returns:
            SystemNotificationEntry instance
        """
        return SystemNotificationEntry(
            content=content,
            notification_type=notification_type,
            timestamp=int(time.time() * 1000),  # milliseconds
        )

    def create_agent_iteration(
        self,
        reasoning: AgentReasoning | None,
        action: dict[str, Any],
        result: dict[str, Any] | None = None,
        validation_errors: list[str] | None = None,
        tool_result: dict[str, Any] | None = None,
    ) -> AgentIterationEntry:
        """Create an agent iteration entry.

        Args:
            reasoning: Agent's reasoning
            action: Action taken by agent
            result: Result from action execution
            validation_errors: Any validation errors
            tool_result: Tool execution result if applicable

        Returns:
            AgentIterationEntry instance
        """
        return AgentIterationEntry(
            reasoning=reasoning,
            action=action,
            result=result,
            validation_errors=validation_errors or [],
            tool_result=tool_result,
            timestamp=int(time.time() * 1000),  # milliseconds
        )

    def build_iteration_history_section(self, iteration_history: list[AgentIterationHistoryEntry] | None) -> list[str]:
        """Build iteration history section for prompt injection.

        Args:
            iteration_history: List of previous iterations

        Returns:
            List of strings representing the history section
        """
        if not iteration_history:
            return []

        history_lines = ["📚 PREVIOUS ITERATIONS:"]
        history_lines.append("Learn from your previous attempts to make better decisions:")

        for i, iteration in enumerate(iteration_history, 1):
            history_lines.append(f"\n--- Iteration {i} ---")

            # Handle different iteration types
            if isinstance(iteration, AgentIterationEntry):
                # Show what the agent tried to do
                if iteration.reasoning:
                    history_lines.append(f"Your reasoning: {iteration.reasoning}")

                if iteration.action:
                    action = iteration.action
                    if action.get("type") == "tool":
                        history_lines.append(f"You called tool: {action.get('tool_name')}")
                        if action.get("parameters"):
                            history_lines.append(f"With parameters: {action['parameters']}")
                    elif action.get("type") == "final_move":
                        move = action.get("move", {})
                        history_lines.append(f"You made final move: {move.get('action')} {move.get('amount', '')}")

                # Show the result/feedback
                if iteration.result:
                    result = iteration.result
                    if result.get("error"):
                        history_lines.append(f"❌ Error: {result['error']}")
                    elif result.get("success"):
                        history_lines.append(f"✅ Tool result: {result}")
                    else:
                        history_lines.append(f"Result: {result}")

                # Show validation errors if any
                if iteration.validation_errors:
                    for error in iteration.validation_errors:
                        history_lines.append(f"❌ Validation error: {error}")

            else:
                # Show system notifications
                history_lines.append(f"🔔 System: {iteration.content}")
                if iteration.notification_type:
                    history_lines.append(f"   Type: {iteration.notification_type}")

        history_lines.append("\n💡 Use this history to avoid repeating mistakes and build on successful tool calls!")
        return history_lines

    def prepare_current_iterations(
        self, existing_iterations: list[AgentIterationHistoryEntry], game_state: dict[str, Any], tool_result: dict[str, Any] | None = None
    ) -> list[AgentIterationHistoryEntry]:
        """Prepare current iterations for LLM processing.

        Args:
            existing_iterations: Existing iteration history
            game_state: Current game state
            tool_result: Optional tool execution result

        Returns:
            List of iterations including new system notifications
        """
        current_iterations = list(existing_iterations)  # Copy existing iterations

        # Add current game state as system notification
        game_state_content = f"Current game state:\n{json.dumps(game_state, indent=2, default=str)}\n\nAnalyze the situation and make your decision."
        current_iterations.append(self.create_system_notification(game_state_content, NotificationType.GAME_STATE))

        # Add tool result if continuing from tool execution
        if tool_result:
            tool_result_content = (
                f"Tool execution completed. Result:\n{json.dumps(tool_result, indent=2)}\n\nNow make your final decision based on this information."
            )
            current_iterations.append(self.create_system_notification(tool_result_content, NotificationType.TOOL_RESULT))

        return current_iterations

"""Agent prompt service for prompt management and processing operations."""

import json
import re
from typing import Any

from game_api import GameType
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.game_env_registry import GameEnvRegistry
from common.utils.template_substitution import substitute_template_variables
from common.utils.utils import get_logger
from shared_db.crud.tool import ToolDAO
from shared_db.models.tool import ToolValidationStatus
from shared_db.schemas.agent import AgentVersionResponse, PromptValidationResult
from shared_db.schemas.game_environments import AgentIterationHistoryEntry
from shared_db.schemas.tool import ToolResponse

logger = get_logger(__name__)


class AgentPromptService:
    """Service layer for agent prompt operations.
    Handles prompt validation, variable substitution, and section injection.
    """

    def __init__(self, tool_dao: ToolDAO | None = None) -> None:
        """Initialize AgentPromptService."""
        self._tool_dao = tool_dao or ToolDAO()

    def substitute_variables(
        self,
        template: str,
        game_state: dict[str, Any],
    ) -> str:
        """Substitute template variables with game state values using Jinja2.

        Args:
            template: Template string with ${{variable}} syntax
            game_state: Game state dictionary

        Returns:
            String with variables substituted
        """
        return substitute_template_variables(template, game_state, strict=False)

    def validate_prompt(self, prompt: str, environment: GameType) -> PromptValidationResult:
        """Validate prompt template and check variable references.

        Args:
            prompt: The prompt template to validate
            environment: The game environment context

        Returns:
            PromptValidationResult with validation status and details
        """
        logger.info(f"Validating prompt for environment {environment}")

        # Extract variables from prompt
        pattern = r"\$\{\{([^}]+)\}\}"
        variables = re.findall(pattern, prompt)

        # Check if prompt contains output format (which is not allowed)
        forbidden_patterns = [
            r"output\s*format",
            r"response\s*format",
            r"json\s*schema",
            r"pydantic",
        ]

        errors: list[str] = []
        for patt in forbidden_patterns:
            if re.search(patt, prompt, re.IGNORECASE):
                errors.append(f"Prompt contains forbidden pattern: {patt}")

        return PromptValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            variable_references=variables,
            warnings=[],
        )

    async def inject_prompt_sections(
        self,
        db: AsyncSession,
        *,
        version: AgentVersionResponse,
        core_prompt: str,
        game_state: dict[str, Any],
        iteration_history: list[AgentIterationHistoryEntry] | None = None,
        environment: GameType,
    ) -> str:
        """Inject tools catalog, output schema, and available moves into the system prompt.

        The final system prompt will include:
        - Core prompt (with substituted variables)
        - Tools catalog: name, description, and parameters (if available)
        - Output JSON schema (AgentDecision)
        - Available moves (if present in game_state under key "available_moves")
        """
        sections: list[str] = []
        sections.append(core_prompt)

        # 1) Tools catalog - dynamic handling using AgentVersionTool relationship
        has_tools = False
        try:
            # Get ordered tools via DAO (Pydantic ToolResponse)
            available_tools: list[ToolResponse] = await self._tool_dao.get_for_agent_version(db, agent_version_id=version.id)
            if not available_tools:
                logger.debug(f"No tools found for agent version {version.id}")

            # Filter out tools that are not validated
            if available_tools:
                before = len(available_tools)
                available_tools = [t for t in available_tools if t.validation_status == ToolValidationStatus.VALID]
                after = len(available_tools)
                if after < before:
                    logger.info(f"Filtered out {before - after} non-valid tools from prompt injection")

            if available_tools:
                has_tools = True
                tool_lines: list[str] = ["🔧 AVAILABLE TOOLS:"]
                tool_lines.append("You have access to the following tools to help with your decision:")

                for tool in available_tools:
                    # Create XML representation of the tool
                    tool_lines.append("\n<tool>")
                    tool_lines.append(f"  <name>{tool.display_name}</name>")

                    # Use the tool's actual description
                    if tool.description:
                        # Split description into lines for better formatting
                        desc_lines = tool.description.strip().split("\n")
                        for i, line in enumerate(desc_lines):
                            if i == 0:
                                tool_lines.append(f"  <description>{line.strip()}</description>")
                            else:
                                tool_lines.append(f"             {line.strip()}")
                    else:
                        tool_lines.append("  <description>No description provided</description>")

                    # Try to extract parameter info from the tool's code or description
                    param_info = self.extract_tool_parameters(tool)
                    if param_info:
                        tool_lines.append("  <parameters>")
                        for param_line in param_info:
                            # Indent parameter lines and wrap in XML tags
                            if param_line.strip().startswith("Parameters"):
                                continue  # Skip the header line
                            tool_lines.append(f"    {param_line.strip()}")
                        tool_lines.append("  </parameters>")
                    else:
                        tool_lines.append("  <parameters>")
                        tool_lines.append("    Check tool documentation for parameter details")
                        tool_lines.append("  </parameters>")

                    tool_lines.append("</tool>")

                logger.debug(f"Adding tools section with {len(available_tools)} tools")
                sections.append("\n" + "\n".join(tool_lines))

                # Add tool usage instructions only if tools are available
                sections.append("\n📋 TOOL USAGE INSTRUCTIONS:")
                sections.append("• To call a tool, use the action field with type='tool', tool_name, and parameters")
                sections.append("• You may ONLY call tools from the list above; do NOT invent tool names")
                allowed = ", ".join([t.name for t in available_tools if t.name])
                sections.append(f"• Allowed tool_name values: {allowed}")
                sections.append("• Read each tool's description and parameter requirements CAREFULLY")
                sections.append("• ALWAYS provide ALL required parameters - never send empty parameters {}")
                sections.append("• Use exact parameter names as specified in the tool description")
                sections.append("• Check parameter formats (arrays, strings, numbers) and provide correct data types")
                sections.append("• Access game state data for tool parameters:")
                sections.append("  - Your player info: state.players[0] (includes chips, status, hole_cards)")
                sections.append("  - Community cards: state.community_cards")
                sections.append("  - Current pot: state.pot")
                sections.append("  - Current bet: state.current_bet")
                sections.append("  - Betting round: state.betting_round (PREFLOP, FLOP, TURN, RIVER, SHOWDOWN)")
                sections.append("• If a tool call fails, read the error message and fix the parameters before trying again")
            else:
                logger.debug("No tools available for this agent")
                sections.append("\n🚫 NO TOOLS AVAILABLE:")
                sections.append("You do not have access to any tools for this decision.")
                sections.append("Make your decision based solely on the game state and your poker knowledge.")
        except Exception as e:
            # Do not fail prompt injection on tools lookup
            logger.error(f"Error injecting tools section: {e}")

        # 2) Iteration history - show previous attempts and results
        if iteration_history:
            from backend.app.services.agent_iteration_service import AgentIterationService

            iteration_service = AgentIterationService()
            history_lines = iteration_service.build_iteration_history_section(iteration_history)
            if history_lines:
                sections.append("\n" + "\n".join(history_lines))

        # 3) Output JSON schema with smart tool instructions
        try:
            schema = GameEnvRegistry.instance().get(environment).types().agent_decision_type().model_json_schema()
            schema_str = json.dumps(schema, indent=2)
            sections.append("\n📋 OUTPUT JSON SCHEMA:\n" + schema_str)

            # Smart instructions based on tool availability
            if has_tools:
                sections.append(
                    "\n🎯 RESPONSE REQUIREMENTS:\n"
                    "• You must respond with a JSON object that strictly matches the schema above\n"
                    "• No extra commentary outside of JSON\n"
                    "• Field order matters: provide 'reasoning' FIRST, then your action, then 'chat_message'\n"
                    "\n⚠️ CRITICAL: Choose EXACTLY ONE action per response:\n"
                    "  1. Call a tool (set 'tool_call' field, leave 'move' and 'exit' as null)\n"
                    "  2. Make a final move (set 'move' field, leave 'tool_call' and 'exit' as null)\n"
                    "  3. Exit the game (set 'exit' field to true, leave 'tool_call' and 'move' as null)\n"
                    "• NEVER set multiple action fields in the same response - this will cause errors\n"
                    "• If you need information before making a move, call a tool first\n"
                    "• After receiving tool results, make your final move in the next response\n"
                    "\n📋 REASONING FIELD (REQUIRED - FILL THIS FIRST):\n"
                    "• The 'reasoning' field explains WHY you chose this specific action\n"
                    "• If calling a tool: explain why you need this information\n"
                    "• If making a move: explain your strategic thinking behind this move\n"
                    "• If exiting: explain why you're leaving the game\n"
                    "\n💬 CHAT MESSAGE:\n"
                    "• REQUIRED when making a move or exiting - must provide a message\n"
                    "• OPTIONAL when calling a tool - can be null\n"
                    "• The message should reflect your agent's personality and the current situation\n"
                    "• Keep it concise but engaging - other players will see this message\n"
                    "\n📝 Tool Usage Guidelines:\n"
                    "• When using tools, the 'parameters' field must contain ALL required tool parameters\n"
                    "• Do NOT send empty parameters {} - always include the required fields\n"
                    "• Double-check parameter names and formats match the tool description exactly\n"
                    "• If you're unsure about a parameter, refer back to the tool description above"
                )
            else:
                sections.append(
                    "\n🎯 RESPONSE REQUIREMENTS:\n"
                    "• You must respond with a JSON object that strictly matches the schema above\n"
                    "• No extra commentary outside of JSON\n"
                    "• Field order matters: provide 'reasoning' FIRST, then your action, then 'chat_message'\n"
                    "• You can either make a final move or exit the game (not both)\n"
                    "• Since you have no tools available, you must make a final move decision using the 'move' field defined in the schema above\n"
                    "\n📋 REASONING FIELD (REQUIRED - FILL THIS FIRST):\n"
                    "• The 'reasoning' field explains WHY you chose this specific action\n"
                    "• If making a move: explain your strategic thinking behind this move\n"
                    "• If exiting: explain why you're leaving the game\n"
                    "\n💬 CHAT MESSAGE (REQUIRED):\n"
                    "• You MUST provide a 'chat_message' when making a move or exiting\n"
                    "• The message should reflect your agent's personality and the current game situation\n"
                    "• Keep it concise but engaging - other players will see this message"
                )
        except Exception:
            pass

        # 4) Available moves (optional): allow the browser to send them in game_state['available_moves']
        available_moves = game_state.get("available_moves")
        if available_moves is not None:
            try:
                sections.append("\n[AVAILABLE_MOVES]\n" + json.dumps(available_moves, indent=2))
            except Exception:
                pass

        final_prompt = "\n\n".join(sections)
        logger.debug(f"Final prompt sections: {len(sections)} sections, total length: {len(final_prompt)}")

        # Pretty print the full prompt for debugging
        logger.info("=" * 80)
        logger.info("🤖 AGENT PROMPT (PRETTY PRINTED)")
        logger.info("=" * 80)
        logger.info(final_prompt)
        logger.info("=" * 80)
        logger.info("END OF AGENT PROMPT")
        logger.info("=" * 80)

        return final_prompt

    def extract_tool_parameters(self, tool: ToolResponse) -> list[str]:
        """Extract parameter information from tool code and description dynamically."""
        param_lines: list[str] = []

        try:
            # First, try to extract from docstring in code
            docstring_params = self._extract_params_from_docstring(tool.code)
            if docstring_params:
                param_lines.extend(docstring_params)
                return param_lines

            # Fallback: Extract from description if it contains structured parameter info
            desc_params = self._extract_params_from_description(tool.description)
            if desc_params:
                param_lines.extend(desc_params)
                return param_lines

            # Final fallback: Generic message
            param_lines.append("  Parameters: See tool description for parameter details")

        except Exception as e:
            logger.debug(f"Error extracting parameters for tool {tool.name}: {e}")
            param_lines.append("  Parameters: Check tool code for parameter requirements")

        return param_lines

    def _extract_params_from_docstring(self, code: str) -> list[str] | None:
        """Extract parameter info from function docstring."""
        try:
            import ast

            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == "lambda_handler":
                    # Extract docstring
                    if (
                        node.body
                        and isinstance(node.body[0], ast.Expr)
                        and isinstance(node.body[0].value, ast.Constant)
                        and isinstance(node.body[0].value.value, str)
                    ):
                        docstring = node.body[0].value.value

                        # Look for parameter section
                        param_section = re.search(
                            r"(?:Parameters?|Args?):\s*\n(.*?)(?:\n\s*\n|\n\s*Returns?|\n\s*Example|\Z)", docstring, re.DOTALL | re.IGNORECASE
                        )

                        if param_section:
                            param_text = param_section.group(1)
                            param_lines = ["  Parameters (from code):"]

                            # Extract individual parameters
                            for line in param_text.split("\n"):
                                line = line.strip()
                                if line and (line.startswith("-") or line.startswith("*") or ":" in line):
                                    # Clean up the line
                                    clean_line = re.sub(r"^[-*]\s*", "• ", line)
                                    param_lines.append(f"    {clean_line}")

                            return param_lines if len(param_lines) > 1 else None
                    break
        except Exception:
            pass
        return None

    def _extract_params_from_description(self, description: str | None) -> list[str] | None:
        """Extract parameter info from tool description."""
        if not description:
            return None

        try:
            # Look for structured parameter sections
            param_section = re.search(
                r"(?:Required\s+)?Parameters?:\s*\n(.*?)(?:\n\s*\n|\n\s*Returns?|\n\s*Example|\Z)", description, re.DOTALL | re.IGNORECASE
            )

            if param_section:
                param_text = param_section.group(1)
                param_lines = ["  Parameters:"]

                # Extract individual parameters
                for line in param_text.split("\n"):
                    line = line.strip()
                    if line and (line.startswith("-") or line.startswith("*") or "`" in line):
                        # Clean up the line and format consistently
                        clean_line = re.sub(r"^[-*]\s*", "• ", line)
                        # Remove excessive backticks and format nicely
                        clean_line = re.sub(r"`([^`]+)`", r"\1", clean_line)
                        param_lines.append(f"    {clean_line}")

                return param_lines if len(param_lines) > 1 else None

        except Exception:
            pass
        return None

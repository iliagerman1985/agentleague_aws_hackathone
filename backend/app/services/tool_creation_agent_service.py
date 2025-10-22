"""Tool creation agent service using Strands.

The agent is completely environment-agnostic and does NOT interact with the database.
It only generates and validates code. The UI handles all persistence.
"""

import re
from collections.abc import AsyncGenerator
from typing import Any

from game_api import GameType
from sqlalchemy.ext.asyncio import AsyncSession
from strands.models.litellm import LiteLLMModel
from strands.types.content import Message, Role

from app.services.game_env_registry import GameEnvRegistry
from app.services.llm_integration_service import LLMIntegrationService
from common.agents.models import AgentResponse, CodeArtifact, ConversationMessage, ToolCreationContext
from common.agents.tool_creation_agent import create_tool_creation_agent
from common.core.app_error import Errors
from common.core.guardrails_service import GuardrailSource, GuardrailsService, GuardrailType
from common.enums import LLMProvider
from common.ids import LLMIntegrationId
from common.utils.utils import get_logger
from shared_db.models.llm_enums import LLMModelType

logger = get_logger()


class ToolCreationAgentService:
    """Service for tool creation agent operations using Strands.

    This service is completely environment-agnostic. It fetches environment context
    from the environment classes and passes it to the agent. The agent does NOT
    interact with the database - it only generates and validates code.
    """

    def __init__(
        self,
        llm_integration_service: LLMIntegrationService,
        game_env_registry: GameEnvRegistry,
        guardrails_service: GuardrailsService,
    ) -> None:
        """Initialize ToolCreationAgentService.

        Args:
            llm_integration_service: LLMIntegrationService for LLM access
            game_env_registry: GameEnvRegistry for environment access
            guardrails_service: GuardrailsService for content validation
        """
        self.llm_integration_service = llm_integration_service
        self.game_env_registry = game_env_registry
        self.guardrails_service = guardrails_service

    def _extract_text_content(self, response: Any) -> str:
        """Extract text content from Strands agent response.

        This method handles the dynamic nature of Strands response objects.
        Strands responses have a content attribute that can be:
        - A string (simple text response)
        - A list of content blocks (text, tool use, etc.)
        - Other types (fallback to string conversion)

        Args:
            response: Strands agent response object (type is dynamic)

        Returns:
            Extracted text content as string
        """
        # Strands responses have a content attribute
        if not hasattr(response, "content"):
            return str(response)

        content = response.content

        # Handle string content directly
        if isinstance(content, str):
            return content

        # Handle list of content blocks
        if isinstance(content, list):
            text_parts: list[str] = []
            for block in content:
                # Handle dict-like blocks with 'text' key
                if isinstance(block, dict):
                    text_value = block.get("text")  # type: ignore[reportUnknownMemberType]
                    if isinstance(text_value, str):
                        text_parts.append(text_value)
                # Handle object-like blocks with 'text' attribute
                elif hasattr(block, "text"):  # type: ignore[reportUnknownArgumentType]
                    text_attr = getattr(block, "text", None)  # type: ignore[reportUnknownArgumentType]
                    if isinstance(text_attr, str):
                        text_parts.append(text_attr)
            return "".join(text_parts) if text_parts else str(response)

        # Fallback for other content types
        return str(content)

    def _extract_test_json(self, content: str) -> str | None:
        """Extract test JSON from response content.

        Looks for ```json blocks and extracts them as test JSON.

        Args:
            content: Response content with potential JSON blocks

        Returns:
            Test JSON string or None if not found
        """
        # Pattern to match ```json blocks
        json_pattern = r"```json\n(.*?)```"
        json_matches = re.findall(json_pattern, content, re.DOTALL)

        if json_matches:
            # Return the first JSON block (should be the test event)
            return json_matches[0].strip()

        return None

    def _extract_code_artifact(self, content: str) -> tuple[str, CodeArtifact | None, str | None, str | None]:
        """Extract code artifact, description, and test JSON from response content.

        Looks for ```tool-function blocks and extracts them as code artifacts.
        Extracts the description from the function's docstring (first line).
        Also extracts ```json blocks as test JSON.
        Removes the tool-function blocks from the content but keeps regular python blocks.

        Args:
            content: Response content with potential code blocks

        Returns:
            Tuple of (cleaned content, code artifact or None, description or None, test JSON or None)
        """
        # Pattern to match ```tool-function blocks
        tool_function_pattern = r"```tool-function\n(.*?)```"
        tool_matches = re.findall(tool_function_pattern, content, re.DOTALL)

        # Extract test JSON
        test_json = self._extract_test_json(content)

        if tool_matches:
            # Extract the last/largest tool-function block
            code = tool_matches[-1].strip()

            # Extract description from the function's docstring
            description: str | None = None
            try:
                # Parse the code to extract docstring
                import ast

                tree = ast.parse(code)

                # Find the lambda_handler function
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.name == "lambda_handler":
                        # Get the full docstring including usage examples
                        docstring = ast.get_docstring(node)
                        if docstring:
                            # Use the full docstring, cleaned up
                            description = docstring.strip()
                        break
            except Exception:
                # If parsing fails, fall back to text before code block
                first_code_block_pos = content.find("```tool-function")
                if first_code_block_pos > 0:
                    before_code = content[:first_code_block_pos].strip()
                    lines = [line.strip() for line in before_code.split("\n") if line.strip()]
                    if lines:
                        description_lines: list[str] = []
                        for line in lines:
                            if not line:
                                break
                            description_lines.append(line)
                        if description_lines:
                            description = " ".join(description_lines)

            code_artifact = CodeArtifact(code=code, language="python", explanation=description) if code else None

            # Remove tool-function blocks from content (keep python blocks for chat display)
            clean_content = re.sub(tool_function_pattern, "", content, flags=re.DOTALL).strip()

            return clean_content, code_artifact, description, test_json

        # No tool-function blocks found
        return content, None, None, test_json

    async def _create_strands_model(
        self,
        db: AsyncSession,
        integration_id: LLMIntegrationId,
        model_id: LLMModelType | None = None,
    ) -> tuple[LiteLLMModel, LLMModelType]:
        """Create a Strands LiteLLM Model from LLM integration.

        Args:
            db: Database session
            integration_id: LLM integration ID
            model_id: Optional specific model to use

        Returns:
            Tuple of (Strands LiteLLM Model instance, model used)
        """
        # Get integration with decrypted API key
        integration = await self.llm_integration_service.get_integration_for_use(db, integration_id)
        if not integration:
            raise ValueError(f"Integration {integration_id} not found")

        # Use specified model or integration's selected model
        model_to_use = model_id or integration.selected_model

        # Build LiteLLM model name (provider/model format)
        provider_map = {
            LLMProvider.OPENAI: "openai",
            LLMProvider.ANTHROPIC: "anthropic",
            LLMProvider.GOOGLE: "gemini",
            LLMProvider.AWS_BEDROCK: "bedrock",
        }

        provider_prefix = provider_map.get(integration.provider)
        if not provider_prefix:
            raise ValueError(f"Unsupported provider: {integration.provider}")

        # For OpenAI, we don't need prefix for standard models
        model_name = str(model_to_use) if integration.provider == LLMProvider.OPENAI else f"{provider_prefix}/{model_to_use}"

        # Create Strands LiteLLM model
        model = LiteLLMModel(
            client_args={
                "api_key": integration.api_key,
            },
            model_id=model_name,
            params={
                "max_tokens": 4000,
                "temperature": 0.7,
            },
        )

        return model, model_to_use

    def _convert_messages_to_strands(
        self,
        conversation_history: list[ConversationMessage],
        new_message: str,
    ) -> list[Message]:
        """Convert conversation history to Strands Message format.

        Args:
            conversation_history: List of previous messages (typed)
            new_message: New user message

        Returns:
            List of Strands Message objects
        """
        messages: list[Message] = []

        # Convert history
        for msg in conversation_history:
            role: Role = "user" if msg.writer == "human" else "assistant"
            messages.append({"role": role, "content": [{"text": msg.content}]})

        # Add new message
        messages.append({"role": "user", "content": [{"text": new_message}]})

        return messages

    async def chat(
        self,
        db: AsyncSession,
        message: str,
        conversation_history: list[ConversationMessage],
        integration_id: LLMIntegrationId,
        environment: GameType,
        model_id: LLMModelType | None = None,
        current_tool_code: str | None = None,
    ) -> AgentResponse[Any]:
        """Process a chat message with the tool creation agent.

        The agent is completely environment-agnostic and does NOT interact with
        the database. It only generates and validates code.

        Args:
            db: Database session (only for LLM integration lookup)
            message: User message
            conversation_history: Previous conversation messages (typed)
            integration_id: LLM integration ID
            environment: Game environment for context
            model_id: Optional specific model to use
            current_tool_code: Optional current tool code being edited

        Returns:
            AgentResponse with typed response and model_used

        Raises:
            AppError: If message violates content policies
        """
        try:
            # Validate message with guardrails
            validation_result = await self.guardrails_service.validate_content(
                content=message,
                guardrail_type=GuardrailType.TOOL_CREATION,
                source=GuardrailSource.INPUT,
            )

            if not validation_result.is_valid:
                violation = validation_result.violation
                if violation:
                    logger.warning(
                        "Tool creation message blocked by guardrail",
                        violated_policies=violation.violated_policies,
                    )

                    # Create a user-friendly error message with policy details
                    policy_names = ", ".join(violation.violated_policies)
                    error_message = (
                        f"Your message was blocked due to content policy violations: {policy_names}. "
                        "Please keep conversations focused on tool creation for your game environment."
                    )

                    raise Errors.Generic.INVALID_INPUT.create(
                        message=error_message,
                        details={
                            "violated_policies": violation.violated_policies,
                            "blocked_message": violation.blocked_message,
                        },
                    )

            # Get environment context from environment class
            env_class = self.game_env_registry.get(environment)
            context: ToolCreationContext[Any, Any, Any] = env_class.get_tool_creation_context()

            # Create Strands model
            model, model_used = await self._create_strands_model(db, integration_id, model_id)

            # Create agent with environment context
            agent = create_tool_creation_agent(
                model=model,
                context=context,
            )

            # Convert messages
            messages = self._convert_messages_to_strands(conversation_history, message)

            # Inject current tool code into context if provided
            agent_context = {
                "current_tool_code": current_tool_code,
                "context": context,  # Pass context to tools
            }

            # Run agent using invoke_async - response type is dynamic from Strands
            response = await agent.invoke_async(messages, context=agent_context)

            # Extract response content using helper method
            raw_content = self._extract_text_content(response)

            # Extract code artifact, description, and test JSON from response
            clean_content, code_artifact, _, test_json = self._extract_code_artifact(raw_content)

            # Check if conversation should be summarized
            should_summarize = len(conversation_history) >= 10

            # Create response with test_json stored separately (not in test_artifact)
            response_obj = AgentResponse[Any](
                content=clean_content,
                code_artifact=code_artifact,
                test_artifact=None,  # Not using TestArtifact for now
                should_summarize=should_summarize,
                model_used=model_used,
            )

            # Store test_json as an attribute for the router to access
            response_obj.test_json = test_json  # type: ignore[attr-defined]

            return response_obj

        except Exception:
            logger.exception("Error in tool creation agent chat")
            raise

    async def stream_chat(
        self,
        db: AsyncSession,
        message: str,
        conversation_history: list[ConversationMessage],
        integration_id: LLMIntegrationId,
        environment: GameType,
        model_id: LLMModelType | None = None,
        current_tool_code: str | None = None,
    ) -> AsyncGenerator[dict[str, Any]]:
        """Stream chat responses from the tool creation agent.

        The agent is completely environment-agnostic and does NOT interact with
        the database. It only generates and validates code.

        Args:
            db: Database session (only for LLM integration lookup)
            message: User message
            conversation_history: Previous conversation messages (typed)
            integration_id: LLM integration ID
            environment: Game environment for context
            model_id: Optional specific model to use
            current_tool_code: Optional current tool code being edited

        Yields:
            Dictionary chunks with agent response
        """
        try:
            # Get environment context from environment class
            env_class = self.game_env_registry.get(environment)
            context: ToolCreationContext[Any, Any, Any] = env_class.get_tool_creation_context()

            # Create Strands model
            model, model_used = await self._create_strands_model(db, integration_id, model_id)

            # Create agent with environment context
            agent = create_tool_creation_agent(
                model=model,
                context=context,
            )

            # Convert messages
            messages = self._convert_messages_to_strands(conversation_history, message)

            # Inject current tool code into context if provided
            agent_context = {
                "current_tool_code": current_tool_code,
                "context": context,  # Pass context to tools
            }

            # Stream agent response using stream_async - stream type is dynamic from Strands
            accumulated_content = ""
            logger.debug("Starting agent stream_async")
            chunk_count = 0
            async for event in agent.stream_async(messages, context=agent_context):
                chunk_count += 1
                logger.debug(f"Received stream event #{chunk_count}: {list(event.keys())}")
                # Extract text content from streaming events
                # Strands streaming events have a "data" field for text chunks
                if "data" in event:
                    content = event["data"]
                    accumulated_content += content
                    logger.debug(f"Yielding content chunk: {content[:100]}...")
                    yield {
                        "type": "content",
                        "content": content,
                        "is_complete": False,
                    }
            logger.info(f"Stream completed. Total chunks: {chunk_count}, accumulated length: {len(accumulated_content)}")

            # Extract code artifact, description, and test JSON from accumulated content
            _, code_artifact, description, test_json = self._extract_code_artifact(accumulated_content)

            # Send completion chunk with code artifact, description, and test JSON
            should_summarize = len(conversation_history) >= 10
            yield {
                "type": "done",
                "is_complete": True,
                "should_summarize": should_summarize,
                "model_used": model_used,
                "code_artifact": code_artifact.model_dump() if code_artifact else None,
                "description": description,
                "test_json": test_json,
            }

        except Exception as e:
            logger.exception("Error in tool creation agent stream")
            yield {
                "type": "error",
                "error": str(e),
                "is_complete": True,
            }

import json
import re
from collections.abc import AsyncGenerator, Callable
from typing import Any, cast, overload

from litellm import acompletion
from litellm.cost_calculator import completion_cost
from pydantic import ValidationError

from common.core.app_error import Errors
from common.core.litellm_schemas import (
    ChatMessage,
    FinishReason,
    FunctionCall,
    LiteLLMConfig,
    LiteLLMFunctionProtocol,
    LiteLLMResponse,
    LiteLLMResponseProtocol,
    LiteLLMStreamChunkProtocol,
    LiteLLMToolCallProtocol,
    MessageRole,
    TokenUsage,
    ToolCallResponse,
    ToolCallType,
)
from common.enums import LLMProvider
from common.model_config import ModelConfigFactory
from common.utils.json_model import TJsonModel
from common.utils.utils import get_logger
from shared_db.schemas.llm_integration import LLMModelType

LiteLLMMessage = dict[str, str]
LiteLLMParams = dict[str, Any]

logger = get_logger()


class LiteLLMService:
    """Service for unified LLM provider interactions using LiteLLM.

    Provides a consistent interface for multiple LLM providers including
    OpenAI, Anthropic, Google, AWS Bedrock, and Azure OpenAI.

    This service implements the BaseLLMService interface for compatibility
    with the LLM service factory pattern.
    """

    def __init__(self) -> None:
        pass

    def _build_model_name(self, provider: LLMProvider, model: LLMModelType) -> str:
        """Build LiteLLM-compatible model name."""
        # LiteLLM expects format: provider/model
        provider_map = {
            LLMProvider.OPENAI: "openai",
            LLMProvider.ANTHROPIC: "anthropic",
            LLMProvider.GOOGLE: "gemini",  # Use direct Gemini API instead of Vertex AI
            LLMProvider.AWS_BEDROCK: "bedrock",
        }

        provider_prefix = provider_map.get(provider)
        if not provider_prefix:
            raise ValueError(f"Unsupported provider: {provider}")

        # For OpenAI, we don't need prefix for standard models
        if provider == LLMProvider.OPENAI:
            return model

        return f"{provider_prefix}/{model}"

    def _prepare_messages(self, messages: list[ChatMessage]) -> list[LiteLLMMessage]:
        """Convert ChatMessage objects to LiteLLM format."""
        # This prevents the exception from bedrock the messages must contain at least one user message
        if len(messages) == 1:
            messages[0].role = MessageRole.USER
        return [{"role": msg.role, "content": msg.content} for msg in messages]

    def _build_request_params(
        self, model_name: str, messages: list[LiteLLMMessage], api_key: str, config: LiteLLMConfig | None = None, aws_credentials: dict[str, str] | None = None
    ) -> LiteLLMParams:
        """Build request parameters for LiteLLM.

        Args:
            model_name: Full model name (e.g., "bedrock/anthropic.claude-haiku-4-5-20251001-v1:0")
            messages: List of messages
            api_key: API key for the provider (or empty string for AWS Bedrock)
            config: Optional configuration
            aws_credentials: Optional AWS credentials dict with keys: aws_access_key_id, aws_secret_access_key, aws_region_name
        """
        params: LiteLLMParams = {
            "model": model_name,
            "messages": messages,
        }

        # Handle AWS Bedrock credentials separately
        if model_name.startswith("bedrock/") and aws_credentials:
            # For AWS Bedrock, pass AWS credentials as separate parameters
            if aws_credentials.get("aws_access_key_id"):
                params["aws_access_key_id"] = aws_credentials["aws_access_key_id"]
            if aws_credentials.get("aws_secret_access_key"):
                params["aws_secret_access_key"] = aws_credentials["aws_secret_access_key"]
            if aws_credentials.get("aws_region_name"):
                params["aws_region_name"] = aws_credentials["aws_region_name"]
        else:
            # For other providers, use api_key
            params["api_key"] = api_key

        if config:
            # Add basic parameters
            if config.max_tokens is not None:
                params["max_tokens"] = config.max_tokens
            if config.temperature is not None:
                params["temperature"] = config.temperature
            if config.top_p is not None:
                params["top_p"] = config.top_p
            if config.stream:
                params["stream"] = True
            if config.tools:
                params["tools"] = config.tools
            if config.tool_choice:
                params["tool_choice"] = config.tool_choice

        # Apply model-specific parameter adjustments
        params = ModelConfigFactory.build_api_params(model_name, params)

        return params

    def _extract_streaming_content(self, chunk: LiteLLMStreamChunkProtocol) -> str | None:
        """Extract content from a streaming chunk safely.

        Args:
            chunk: Streaming chunk from LiteLLM

        Returns:
            Content string if available, None otherwise
        """
        try:
            if hasattr(chunk, "choices") and chunk.choices and len(chunk.choices) > 0:
                choice = chunk.choices[0]
                if hasattr(choice, "delta") and choice.delta and hasattr(choice.delta, "content") and choice.delta.content:
                    return str(choice.delta.content)
        except (AttributeError, IndexError, TypeError):
            # Skip malformed chunks
            pass
        return None

    def _extract_and_clean_json(self, content: str) -> str:
        """Extract and clean JSON from LLM response content.

        Args:
            content: Raw content from LLM response

        Returns:
            Cleaned JSON string

        Raises:
            ValueError: If no valid JSON is found
        """
        # First try to extract JSON using balanced brace counting
        json_str = self._extract_json_with_brace_counting(content)

        if not json_str:
            # Fallback to regex patterns
            json_patterns = [
                # Try to find JSON objects with balanced braces
                r"\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\})*)*\}))*\}",
                # Greedy approach as last resort
                r"\{.*\}",
            ]

            for i, pattern in enumerate(json_patterns):
                match = re.search(pattern, content, re.DOTALL)
                if match:
                    json_str = match.group()
                    logger.debug(f"JSON extraction: regex pattern {i + 1} matched, extracted {len(json_str)} characters")
                    break

        if not json_str:
            logger.warning(f"No JSON found in content: {content[:500]}...")
            raise ValueError("No JSON found in content")

        # Clean common issues in LLM-generated JSON
        json_str = json_str.strip()

        # Handle literal \n sequences that should be actual newlines
        json_str = json_str.replace("\\n", "\n").replace("\\t", "\t")

        # Try parsing as-is first
        try:
            parsed = json.loads(json_str)
            logger.debug("JSON parsed successfully on first attempt")
            return json.dumps(parsed)
        except json.JSONDecodeError as e:
            logger.debug(f"First JSON parse failed: {e} at position {e.pos}")
            # Log the problematic area
            if hasattr(e, "pos") and e.pos:
                start = max(0, e.pos - 50)
                end = min(len(json_str), e.pos + 50)
                problematic_area = json_str[start:end]
                logger.debug(f"Problematic JSON area: ...{problematic_area}...")

        # If that fails, try multiple fixing strategies
        fixing_strategies: list[Callable[[str], str]] = [
            # Strategy 1: Simple quote replacement
            lambda s: s.replace("'", '"'),
            # Strategy 2: More sophisticated quote replacement that preserves apostrophes
            lambda s: self._smart_quote_replacement(s),
            # Strategy 3: Handle control characters
            lambda s: s.replace("\n", "\\n").replace("\t", "\\t").replace("\r", "\\r"),
        ]

        last_error = None
        for i, strategy in enumerate(fixing_strategies):
            try:
                fixed_json = strategy(json_str)
                parsed = json.loads(fixed_json)
                logger.debug(f"JSON parsed successfully after fixing strategy {i + 1}")
                return json.dumps(parsed)
            except json.JSONDecodeError as e:
                logger.debug(f"Fixing strategy {i + 1} failed: {e}")
                last_error = e
                continue

        # If all strategies fail, provide detailed error logging
        logger.warning(f"All JSON cleaning strategies failed. Original length: {len(json_str)}")
        logger.warning(f"Original JSON preview: {json_str[:200]}...")
        raise ValueError("Could not parse JSON after trying all cleaning strategies") from last_error

    def _extract_json_with_brace_counting(self, content: str) -> str | None:
        """Extract JSON using balanced brace counting to find the outermost JSON object.

        This method finds the first '{' and then counts braces to find the matching '}'.
        It handles strings properly by ignoring braces inside quoted strings.

        Args:
            content: Raw content that may contain JSON

        Returns:
            Extracted JSON string or None if no valid JSON found
        """
        # Find the first opening brace
        start_idx = content.find("{")
        if start_idx == -1:
            return None

        brace_count = 0
        in_string = False
        escape_next = False

        for i in range(start_idx, len(content)):
            char = content[i]

            if escape_next:
                escape_next = False
                continue

            if char == "\\" and in_string:
                escape_next = True
                continue

            if char == '"' and not escape_next:
                in_string = not in_string
                continue

            if not in_string:
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1

                    # Found the matching closing brace
                    if brace_count == 0:
                        json_str = content[start_idx : i + 1]
                        logger.debug(f"JSON extraction: brace counting found JSON of {len(json_str)} characters")
                        return json_str

        # If we get here, braces weren't balanced
        logger.debug("JSON extraction: brace counting failed - unbalanced braces")
        return None

    def _smart_quote_replacement(self, json_str: str) -> str:
        """Replace single quotes with double quotes while preserving apostrophes in values.

        This is a heuristic approach that works for most common cases.
        """
        result: list[str] = []
        i = 0
        in_string = False
        string_delimiter: str | None = None

        while i < len(json_str):
            char = json_str[i]

            if not in_string:
                if char == "'":
                    # Check if this looks like a property key or string value start
                    # Look ahead to see if this is likely a key (followed by :) or value
                    ahead = json_str[i + 1 :].lstrip()
                    if ahead and (ahead[0].isalnum() or ahead[0] == "_"):
                        # This looks like the start of a key or simple value
                        result.append('"')
                        in_string = True
                        string_delimiter = "'"
                    else:
                        result.append(char)
                else:
                    result.append(char)
                    if char == '"':
                        in_string = True
                        string_delimiter = '"'
            elif char == string_delimiter:
                if string_delimiter == "'":
                    result.append('"')
                else:
                    result.append(char)
                in_string = False
                string_delimiter = None
            elif char == '"' and string_delimiter == "'":
                # Escape double quotes inside single-quoted strings
                result.append('\\"')
            else:
                result.append(char)

            i += 1

        return "".join(result)

    def _parse_response(
        self, response: LiteLLMResponseProtocol, output_type: type[TJsonModel] | type[str], original_model: LLMModelType
    ) -> LiteLLMResponse[TJsonModel] | LiteLLMResponse[str]:
        """Parse LiteLLM response into our schema.

        Args:
            response: Raw response from LiteLLM
            output_type: Expected output type
            original_model: The original model enum we sent (LiteLLM may return a different format)
        """
        choice = response.choices[0]
        message = choice.message

        content: TJsonModel | str | None = None
        if message.content:
            if output_type is str:
                content = message.content
            else:
                try:
                    cleaned_json_str = self._extract_and_clean_json(message.content)
                    content = output_type.model_validate_json(cleaned_json_str)  # type: ignore
                except Exception as e:
                    error_message = e.json() if isinstance(e, ValidationError) else str(e)
                    raise Errors.Agent.INVALID_OUTPUT.create(
                        f"You did not return valid JSON: {error_message}", details={"model": original_model, "raw_content": message.content, "error": str(e)}
                    ) from e

        tool_calls: list[ToolCallResponse] | None = None
        if hasattr(message, "tool_calls") and message.tool_calls:
            tool_calls = []
            for tc in message.tool_calls:
                # Cast to protocol for type safety
                typed_tc: LiteLLMToolCallProtocol = tc

                # Extract function data with proper typing
                func: LiteLLMFunctionProtocol = typed_tc.function

                # Try to get data as dict first, fallback to direct access
                func_data: dict[str, str]
                if hasattr(func, "model_dump"):
                    func_data = func.model_dump()
                else:
                    # Fallback for direct attribute access
                    func_data = {"name": getattr(func, "name", ""), "arguments": getattr(func, "arguments", "{}")}

                function_call = FunctionCall(name=func_data.get("name", ""), arguments=func_data.get("arguments", "{}"))

                # Parse tool call type safely
                tool_type = ToolCallType.FUNCTION
                if hasattr(typed_tc, "type") and typed_tc.type:
                    try:
                        tool_type = ToolCallType(typed_tc.type)
                    except ValueError:
                        tool_type = ToolCallType.FUNCTION

                tool_call = ToolCallResponse(id=typed_tc.id, type=tool_type, function=function_call)
                tool_calls.append(tool_call)

        # Parse finish reason safely
        finish_reason: FinishReason | None = None
        if hasattr(choice, "finish_reason") and choice.finish_reason:
            try:
                finish_reason = FinishReason(choice.finish_reason)
            except ValueError:
                # If the finish reason is not in our enum, keep it as None
                finish_reason = None

        # Extract token usage information
        usage: TokenUsage | None = None
        if response.usage:
            usage_data = response.usage
            usage = TokenUsage(
                prompt_tokens=getattr(usage_data, "prompt_tokens", 0),
                completion_tokens=getattr(usage_data, "completion_tokens", 0),
                total_tokens=getattr(usage_data, "total_tokens", 0),
            )

        # Calculate cost using LiteLLM's completion_cost function
        cost_usd: float | None = None
        if usage:
            try:
                cost_usd = completion_cost(completion_response=response)
            except Exception as e:
                logger.warning(f"Failed to calculate cost: {e!s}")
                cost_usd = None

        return LiteLLMResponse(
            content=content,  # type: ignore
            tool_calls=tool_calls,
            model=original_model,  # Use the original model we sent, not what LiteLLM returns
            finish_reason=finish_reason,
            usage=usage,
            cost_usd=cost_usd,
        )

    @overload
    async def chat_completion(
        self,
        provider: LLMProvider,
        model: LLMModelType,
        messages: list[ChatMessage],
        api_key: str,
        output_type: type[TJsonModel],
        config: LiteLLMConfig | None = None,
        aws_credentials: dict[str, str] | None = None,
    ) -> LiteLLMResponse[TJsonModel]: ...

    @overload
    async def chat_completion(
        self,
        provider: LLMProvider,
        model: LLMModelType,
        messages: list[ChatMessage],
        api_key: str,
        output_type: type[str],
        config: LiteLLMConfig | None = None,
        aws_credentials: dict[str, str] | None = None,
    ) -> LiteLLMResponse[str]: ...

    async def chat_completion(
        self,
        provider: LLMProvider,
        model: LLMModelType,
        messages: list[ChatMessage],
        api_key: str,
        output_type: type[TJsonModel] | type[str],
        config: LiteLLMConfig | None = None,
        aws_credentials: dict[str, str] | None = None,
    ) -> LiteLLMResponse[TJsonModel] | LiteLLMResponse[str]:
        """Generate a single chat completion response.

        Args:
            provider: LLM provider enum
            model: Model name to use
            messages: List of chat messages
            api_key: API key for the provider (or empty string for AWS Bedrock)
            output_type: Type of the output
            config: Optional configuration for the request
            aws_credentials: Optional AWS credentials dict for Bedrock (keys: aws_access_key_id, aws_secret_access_key, aws_region_name)

        Returns:
            LiteLLM response with parsed content, or parsed Pydantic object if output_schema provided

        Raises:
            Exception: If the completion request fails
        """
        try:
            model_name = self._build_model_name(provider, model)
            working_messages = self._prepare_messages(messages)

            params = self._build_request_params(model_name, working_messages, api_key, config, aws_credentials)

            logger.info("Completion parameters", model=model_name, provider=provider.value, params=params)
            raw_response = await acompletion(**params)

            # Cast to protocol for type safety
            # Pass the original model enum to preserve type safety (LiteLLM may return a different format)
            parsed_response = self._parse_response(cast(LiteLLMResponseProtocol, raw_response), output_type, model)
            logger.info("Completion generated successfully", content=parsed_response.content, tool_calls=parsed_response.tool_calls)

            return parsed_response

        except Exception as e:
            logger.exception(f"Error in chat completion for {provider.value}/{model}")
            raise e

    async def stream_chat_completion(
        self,
        provider: LLMProvider,
        model: LLMModelType,
        messages: list[ChatMessage],
        api_key: str,
        config: LiteLLMConfig | None = None,
        aws_credentials: dict[str, str] | None = None,
    ) -> AsyncGenerator[str]:
        """Stream chat completion response.

        Args:
            provider: LLM provider enum
            model: Model name to use
            messages: List of chat messages
            api_key: API key for the provider (or empty string for AWS Bedrock)
            config: Optional configuration for the request
            aws_credentials: Optional AWS credentials dict for Bedrock (keys: aws_access_key_id, aws_secret_access_key, aws_region_name)

        Yields:
            Streaming response chunks as strings

        Raises:
            Exception: If the streaming request fails
        """
        try:
            model_name = self._build_model_name(provider, model)
            litellm_messages = self._prepare_messages(messages)

            logger.info(f"Starting streaming completion with {model_name}")

            # Ensure streaming is enabled
            stream_config = config or LiteLLMConfig()
            stream_config.stream = True

            params = self._build_request_params(model_name, litellm_messages, api_key, stream_config, aws_credentials)

            response = await acompletion(**params)

            # Process streaming response with proper typing
            # LiteLLM returns an async iterable when stream=True
            # Cast to AsyncGenerator for proper typing
            async_response = cast("AsyncGenerator[Any]", response)
            chunk_count = 0
            yielded_chars = 0
            async for chunk in async_response:
                chunk_protocol = cast("LiteLLMStreamChunkProtocol", chunk)
                content = self._extract_streaming_content(chunk_protocol)
                if content:
                    yielded_chars += len(content)
                    yield content
                # Log first few chunks with no content for diagnostics (truncated)
                elif chunk_count < 3:
                    try:
                        raw_preview = repr(chunk_protocol)
                    except Exception:
                        raw_preview = "<unrepr-able>"
                    logger.debug(
                        "Streaming chunk with no content",
                        provider=provider.value,
                        model=model_name,
                        index=chunk_count,
                        raw=raw_preview[:1000],
                    )
                chunk_count += 1

            # Final diagnostics
            if yielded_chars == 0:
                logger.warning(
                    "Streaming completed with 0 content characters",
                    provider=provider.value,
                    model=model_name,
                    chunk_count=chunk_count,
                    params={k: v for k, v in params.items() if k != "api_key"},
                )

        except Exception as e:
            logger.exception("Error in streaming chat completion")
            raise Exception(f"LiteLLM streaming completion failed: {e!s}") from e

    async def test_connection(
        self,
        provider: LLMProvider,
        model: LLMModelType,
        api_key: str,
        test_message: str = "Hello, please respond with 'Connection successful'",
    ) -> bool:
        """Test connection to a provider.

        Args:
            provider: LLM provider enum
            model: Model name to test
            api_key: API key for the provider
            output_type: Type of the output
            test_message: Test message to send

        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Create a simple test message
            test_messages = [ChatMessage(role=MessageRole.USER, content=test_message)]

            response = await self.chat_completion(
                provider=provider,
                model=model,
                messages=test_messages,
                api_key=api_key,
                output_type=str,
                config=LiteLLMConfig(max_tokens=50, temperature=0.1),
            )

            logger.info(f"Connection test successful: {response.content[:100] if response.content else 'No content'}...")
            return True

        except Exception:
            logger.exception(f"Connection test failed for {provider.value}/{model}")
            return False

    def get_supported_providers(self) -> list[LLMProvider]:
        """Get list of supported providers.

        Returns:
            List of supported provider enums
        """
        # Return all providers that LiteLLM supports
        return [
            LLMProvider.OPENAI,
            LLMProvider.ANTHROPIC,
            LLMProvider.GOOGLE,
            LLMProvider.AWS_BEDROCK,
            # Note: AWS_BEDROCK would need additional configuration
        ]


# Note: Global service instance moved to dependencies.py for proper dependency injection

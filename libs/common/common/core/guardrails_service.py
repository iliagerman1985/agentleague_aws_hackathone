"""AWS Bedrock Guardrails service for content validation."""

from enum import StrEnum
from typing import Any, cast

from botocore.exceptions import ClientError
from types_aiobotocore_bedrock_runtime import BedrockRuntimeClient

from common.core.aws_manager import AwsManager
from common.core.config_service import config_service
from common.utils.json_model import JsonModel
from common.utils.utils import get_logger

logger = get_logger(__name__)


class GuardrailAction(StrEnum):
    """Guardrail action types."""

    NONE = "NONE"
    GUARDRAIL_INTERVENED = "GUARDRAIL_INTERVENED"


class GuardrailSource(StrEnum):
    """Source of content being evaluated."""

    INPUT = "INPUT"
    OUTPUT = "OUTPUT"


class GuardrailType(StrEnum):
    """Types of guardrails available."""

    AGENT_INSTRUCTIONS = "agent_instructions"
    TOOL_CREATION = "tool_creation"


class ContentPolicyViolation(JsonModel):
    """Details about a content policy violation."""

    filter_type: str
    confidence: str
    action: str


class TopicPolicyViolation(JsonModel):
    """Details about a topic policy violation."""

    topic_name: str
    topic_type: str
    action: str


class WordPolicyViolation(JsonModel):
    """Details about a word policy violation."""

    matched_word: str
    action: str


class GuardrailViolation(JsonModel):
    """Details about a guardrail violation."""

    violated_policies: list[str]
    action: GuardrailAction
    blocked_message: str | None = None

    # Detailed assessment information
    content_policy_violations: list[ContentPolicyViolation] | None = None
    topic_policy_violations: list[TopicPolicyViolation] | None = None
    word_policy_violations: list[WordPolicyViolation] | None = None


class GuardrailValidationResult(JsonModel):
    """Result of guardrail validation."""

    is_valid: bool
    violation: GuardrailViolation | None = None
    original_content: str
    sanitized_content: str | None = None  # If masking was applied
    guardrail_id: str | None = None  # ID of guardrail used
    guardrail_version: str | None = None  # Version of guardrail used


class GuardrailConfig(JsonModel):
    """Configuration for a specific guardrail."""

    guardrail_id: str
    version: str


class GuardrailsService:
    """Service for validating content using AWS Bedrock Guardrails.

    Uses the centralized AwsManager for client creation, which handles:
    - Loading credentials from secrets.yaml (local dev)
    - Using IAM roles/IRSA (cloud environments)
    - Proper lifecycle management of async clients
    """

    def __init__(self, aws_manager: AwsManager) -> None:
        """Initialize the guardrails service.

        Args:
            aws_manager: Centralized AWS service manager with bedrock-runtime client
        """
        self._config = config_service
        self._aws_manager = aws_manager

        # Load guardrail configurations
        agent_instructions_id = self._config.get("GUARDRAIL_AGENT_INSTRUCTIONS_ID")
        agent_instructions_version = "3"  # Hardcoded to version 3 - PROMPT_ATTACK filter removed
        tool_creation_id = self._config.get("GUARDRAIL_TOOL_CREATION_ID")
        tool_creation_version = self._config.get("GUARDRAIL_TOOL_CREATION_VERSION", "1")

        self._guardrails: dict[GuardrailType, GuardrailConfig] = {}

        if agent_instructions_id:
            self._guardrails[GuardrailType.AGENT_INSTRUCTIONS] = GuardrailConfig(
                guardrail_id=agent_instructions_id,
                version=agent_instructions_version,
            )

        if tool_creation_id:
            self._guardrails[GuardrailType.TOOL_CREATION] = GuardrailConfig(
                guardrail_id=tool_creation_id,
                version=tool_creation_version,
            )

        logger.info(
            "Initialized GuardrailsService",
            region=self._config.aws.region,
            has_explicit_credentials=self._config.aws.has_credentials(),
            guardrails_config={str(gt): {"id": gc.guardrail_id, "version": gc.version} for gt, gc in self._guardrails.items()},
        )

    async def validate_content(
        self,
        content: str,
        guardrail_type: GuardrailType,
        source: GuardrailSource = GuardrailSource.INPUT,
    ) -> GuardrailValidationResult:
        """Validate content using specified guardrail.

        Args:
            content: Content to validate
            guardrail_type: Type of guardrail to use
            source: Whether this is INPUT or OUTPUT content

        Returns:
            GuardrailValidationResult with validation details

        Raises:
            ValueError: If guardrail not configured
            ClientError: If AWS API call fails
        """
        guardrail_config = self._guardrails.get(guardrail_type)
        if not guardrail_config:
            raise ValueError(f"Guardrail {guardrail_type} not configured")

        logger.info(
            "Validating content with guardrail",
            guardrail_type=guardrail_type.value,
            guardrail_id=guardrail_config.guardrail_id,
            content_length=len(content),
        )

        try:
            # Use centralized bedrock-runtime client from AwsManager
            # This client is already configured with proper credentials (from secrets.yaml or IAM role)
            client: BedrockRuntimeClient = self._aws_manager.bedrock_runtime_client

            # Call ApplyGuardrail API asynchronously
            response_raw = await client.apply_guardrail(
                guardrailIdentifier=guardrail_config.guardrail_id,
                guardrailVersion=guardrail_config.version,
                source=source.value,
                content=[{"text": {"text": content}}],
            )
            # Cast to ensure type checker knows this is a dict
            response = cast(dict[str, Any], response_raw)

            action_str = cast(str, response.get("action", "NONE"))
            action = GuardrailAction(action_str)

            if action == GuardrailAction.GUARDRAIL_INTERVENED:
                # Extract violation details
                violation = self._parse_violation(response)

                logger.warning(
                    "Guardrail blocked content",
                    guardrail_type=guardrail_type.value,
                    guardrail_id=guardrail_config.guardrail_id,
                    guardrail_version=guardrail_config.version,
                    violated_policies=violation.violated_policies,
                )

                return GuardrailValidationResult(
                    is_valid=False,
                    violation=violation,
                    original_content=content,
                    guardrail_id=guardrail_config.guardrail_id,
                    guardrail_version=guardrail_config.version,
                )

            # Content passed validation
            logger.info("Content passed guardrail validation", guardrail_type=guardrail_type.value)

            # Check if any masking was applied (for sensitive information)
            sanitized_content: str | None = None
            outputs_raw = response.get("outputs")
            outputs = cast(list[dict[str, Any]], outputs_raw) if outputs_raw is not None else []
            if len(outputs) > 0:
                first_output = outputs[0]
                sanitized_content = cast(str | None, first_output.get("text"))

            return GuardrailValidationResult(
                is_valid=True,
                violation=None,
                original_content=content,
                sanitized_content=sanitized_content,
                guardrail_id=guardrail_config.guardrail_id,
                guardrail_version=guardrail_config.version,
            )

        except ClientError as e:
            logger.exception(
                "Failed to validate content with guardrail",
                guardrail_type=guardrail_type.value,
                error=str(e),
            )
            raise

    def _parse_violation(self, response: dict[str, Any]) -> GuardrailViolation:
        """Parse violation details from guardrail response.

        Args:
            response: Response from ApplyGuardrail API

        Returns:
            GuardrailViolation with parsed details
        """
        violated_policies: list[str] = []
        content_violations: list[ContentPolicyViolation] = []
        topic_violations: list[TopicPolicyViolation] = []
        word_violations: list[WordPolicyViolation] = []

        assessments = response.get("assessments", [])

        for assessment in assessments:
            # Content policy violations
            content_policy = assessment.get("contentPolicy", {})
            filters = content_policy.get("filters", [])
            for filter_result in filters:
                if filter_result.get("action") == "BLOCKED":
                    filter_type = filter_result.get("type", "UNKNOWN")
                    violated_policies.append(f"content_{filter_type.lower()}")
                    content_violations.append(
                        ContentPolicyViolation(
                            filter_type=filter_type,
                            confidence=filter_result.get("confidence", "UNKNOWN"),
                            action=filter_result.get("action", "UNKNOWN"),
                        )
                    )

            # Topic policy violations
            topic_policy = assessment.get("topicPolicy", {})
            topics = topic_policy.get("topics", [])
            for topic in topics:
                if topic.get("action") == "BLOCKED":
                    topic_name = topic.get("name", "UNKNOWN")
                    violated_policies.append(f"topic_{topic_name}")
                    topic_violations.append(
                        TopicPolicyViolation(
                            topic_name=topic_name,
                            topic_type=topic.get("type", "UNKNOWN"),
                            action=topic.get("action", "UNKNOWN"),
                        )
                    )

            # Word policy violations
            word_policy = assessment.get("wordPolicy", {})
            custom_words = word_policy.get("customWords", [])
            for word in custom_words:
                if word.get("action") == "BLOCKED":
                    violated_policies.append("word_filter")
                    word_violations.append(
                        WordPolicyViolation(
                            matched_word=word.get("match", "UNKNOWN"),
                            action=word.get("action", "UNKNOWN"),
                        )
                    )

        # Get blocked message from outputs
        blocked_message = None
        outputs = response.get("outputs", [])
        if outputs and len(outputs) > 0:
            blocked_message = outputs[0].get("text")

        return GuardrailViolation(
            violated_policies=violated_policies,
            action=GuardrailAction.GUARDRAIL_INTERVENED,
            blocked_message=blocked_message,
            content_policy_violations=content_violations if content_violations else None,
            topic_policy_violations=topic_violations if topic_violations else None,
            word_policy_violations=word_violations if word_violations else None,
        )

"""Agent version service for version management operations."""

from sqlalchemy.ext.asyncio import AsyncSession

from common.core.app_error import Errors
from common.core.guardrails_service import GuardrailSource, GuardrailsService, GuardrailType
from common.ids import AgentId, AgentVersionId, UserId
from common.utils.utils import get_logger
from shared_db.crud.agent import AgentDAO, AgentVersionDAO
from shared_db.schemas.agent import (
    AgentVersionComparisonResponse,
    AgentVersionCreate,
    AgentVersionLimitInfo,
    AgentVersionResponse,
    AgentVersionUpdate,
)

logger = get_logger(__name__)


class AgentVersionService:
    """Service layer for agent version operations.
    Handles version-specific business logic and coordinates between routers and DAOs.
    """

    def __init__(
        self,
        agent_dao: AgentDAO,
        agent_version_dao: AgentVersionDAO,
        guardrails_service: GuardrailsService,
    ) -> None:
        """Initialize AgentVersionService with DAO dependencies.

        Args:
            agent_dao: AgentDAO instance for agent operations
            agent_version_dao: AgentVersionDAO instance for version operations
            guardrails_service: GuardrailsService instance for content validation
        """
        self.agent_dao = agent_dao
        self.agent_version_dao = agent_version_dao
        self.guardrails_service = guardrails_service

    async def _validate_instructions(
        self,
        system_prompt: str,
        conversation_instructions: str | None,
    ) -> None:
        """Validate agent instructions using guardrails.

        Args:
            system_prompt: System prompt to validate
            conversation_instructions: Conversation instructions to validate

        Raises:
            AppError: If instructions violate content policies
        """
        # Combine system prompt and conversation instructions for validation
        combined_instructions = system_prompt
        if conversation_instructions:
            combined_instructions += f"\n\n{conversation_instructions}"

        validation_result = await self.guardrails_service.validate_content(
            content=combined_instructions,
            guardrail_type=GuardrailType.AGENT_INSTRUCTIONS,
            source=GuardrailSource.INPUT,
        )

        if not validation_result.is_valid:
            violation = validation_result.violation
            if violation:
                logger.warning(
                    "Agent instructions blocked by guardrail",
                    guardrail_id=validation_result.guardrail_id,
                    guardrail_version=validation_result.guardrail_version,
                    violated_policies=violation.violated_policies,
                )

                # Create a user-friendly error message with policy details
                policy_names = ", ".join(violation.violated_policies)
                error_message = (
                    f"Your agent instructions were blocked due to content policy violations: {policy_names}. "
                    f"(Guardrail: {validation_result.guardrail_id} v{validation_result.guardrail_version}) "
                    "Please review and revise your instructions to comply with our usage policies."
                )

                raise Errors.Generic.INVALID_INPUT.create(
                    message=error_message,
                    details={
                        "violated_policies": violation.violated_policies,
                        "blocked_message": violation.blocked_message,
                        "guardrail_id": validation_result.guardrail_id,
                        "guardrail_version": validation_result.guardrail_version,
                    },
                )

    async def get_agent_versions(
        self,
        db: AsyncSession,
        *,
        user_id: UserId,
        agent_id: AgentId,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AgentVersionResponse]:
        """Get all versions for an agent.

        Args:
            db: Database session
            user_id: User ID
            agent_id: Agent ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of AgentVersionResponse objects
        """
        logger.info(f"Getting versions for agent {agent_id}")

        # Verify agent ownership
        agent = await self.agent_dao.get_by_user_and_id(db, user_id=user_id, agent_id=agent_id)
        if not agent:
            return []

        return await self.agent_version_dao.get_by_agent(db, agent_id=agent_id, skip=skip, limit=limit)

    async def get_active_version(
        self,
        db: AsyncSession,
        *,
        user_id: UserId,
        agent_id: AgentId,
    ) -> AgentVersionResponse | None:
        """Get the active version for an agent.

        Args:
            db: Database session
            user_id: User ID
            agent_id: Agent ID

        Returns:
            Active AgentVersionResponse if found, None otherwise
        """
        logger.info(f"Getting active version for agent {agent_id}")

        # Verify agent ownership
        agent = await self.agent_dao.get_by_user_and_id(db, user_id=user_id, agent_id=agent_id)
        if not agent:
            return None

        return await self.agent_version_dao.get_active_version(db, agent_id=agent_id)

    async def create_version(
        self,
        db: AsyncSession,
        *,
        user_id: UserId,
        agent_id: AgentId,
        version_in: AgentVersionCreate,
    ) -> AgentVersionResponse | None:
        """Create a new version for an agent.

        Args:
            db: Database session
            user_id: User ID
            agent_id: Agent ID
            version_in: Version creation data

        Returns:
            Created AgentVersionResponse if successful, None if agent not found

        Raises:
            AppError: If instructions violate content policies
        """
        logger.info(f"Creating version for agent {agent_id}")

        # Verify agent ownership
        agent = await self.agent_dao.get_by_user_and_id(db, user_id=user_id, agent_id=agent_id)
        if not agent:
            return None

        # Validate instructions with guardrails
        await self._validate_instructions(
            system_prompt=version_in.system_prompt,
            conversation_instructions=version_in.conversation_instructions,
        )

        return await self.agent_version_dao.create(db, obj_in=version_in, agent_id=agent_id, user_id=user_id)

    async def update_version(
        self,
        db: AsyncSession,
        *,
        user_id: UserId,
        agent_id: AgentId,
        version_id: AgentVersionId,
        version_in: AgentVersionUpdate,
    ) -> AgentVersionResponse | None:
        """Update a version (creates new version if version-defining fields change).

        Args:
            db: Database session
            user_id: User ID
            agent_id: Agent ID
            version_id: Version ID
            version_in: Version update data

        Returns:
            Updated or new AgentVersionResponse if successful, None otherwise
        """
        logger.info(f"Updating version {version_id} for agent {agent_id}")

        # Verify agent ownership
        agent = await self.agent_dao.get_by_user_and_id(db, user_id=user_id, agent_id=agent_id)
        if not agent:
            return None

        # Get the version using DAO
        version = await self.agent_version_dao.get_with_tools(db, version_id=version_id)
        if not version or version.agent_id != agent_id:
            return None

        # Check if this update requires a new version
        if version_in.has_version_defining_changes():
            # Create a new version with the changes
            version_defining_fields = version_in.get_version_defining_fields()

            # Start with current version's values
            new_version_data = AgentVersionCreate(
                system_prompt=version.system_prompt,
                conversation_instructions=version.conversation_instructions,
                exit_criteria=version.exit_criteria,
                tool_ids=version.tool_ids or [],
                slow_llm_provider=version.slow_llm_provider,
                fast_llm_provider=version.fast_llm_provider,
                slow_llm_model=version.slow_llm_model,
                fast_llm_model=version.fast_llm_model,
                timeout=version.timeout,
                max_iterations=version.max_iterations,
            )

            # Apply the version-defining changes
            for field, value in version_defining_fields.items():
                setattr(new_version_data, field, value)

            # Apply any configuration changes
            config_fields = version_in.get_configuration_fields()
            for field, value in config_fields.items():
                setattr(new_version_data, field, value)

            # Validate instructions if they changed
            if version_in.system_prompt is not None or version_in.conversation_instructions is not None:
                await self._validate_instructions(
                    system_prompt=new_version_data.system_prompt,
                    conversation_instructions=new_version_data.conversation_instructions,
                )

            return await self.agent_version_dao.create(db, obj_in=new_version_data, agent_id=agent_id, user_id=user_id)
        else:
            # Just update configuration fields using DAO
            return await self.agent_version_dao.update_by_id(db, id=version_id, obj_in=version_in)

    async def activate_version(
        self,
        db: AsyncSession,
        *,
        user_id: UserId,
        agent_id: AgentId,
        version_id: AgentVersionId,
    ) -> AgentVersionResponse | None:
        """Activate a specific version of an agent.

        Args:
            db: Database session
            user_id: User ID
            agent_id: Agent ID
            version_id: Version ID to activate

        Returns:
            Activated AgentVersionResponse if successful, None otherwise
        """
        logger.info(f"Activating version {version_id} for agent {agent_id}")

        # Verify agent ownership
        agent = await self.agent_dao.get_by_user_and_id(db, user_id=user_id, agent_id=agent_id)
        if not agent:
            return None

        # Verify version belongs to this agent
        version = await self.agent_version_dao.get(db, id=version_id)
        if not version or version.agent_id != agent_id:
            return None

        return await self.agent_version_dao.activate(db, version_id=version_id)

    async def get_version_limit_info(
        self,
        db: AsyncSession,
        *,
        user_id: UserId,
        agent_id: AgentId,
    ) -> AgentVersionLimitInfo | None:
        """Get version limit information for an agent.

        Args:
            db: Database session
            user_id: User ID
            agent_id: Agent ID

        Returns:
            AgentVersionLimitInfo if agent found, None otherwise
        """
        logger.info(f"Getting version limit info for agent {agent_id}")

        # Verify agent ownership
        agent = await self.agent_dao.get_by_user_and_id(db, user_id=user_id, agent_id=agent_id)
        if not agent:
            return None

        versions = await self.agent_version_dao.get_by_agent(db, agent_id=agent_id)

        return AgentVersionLimitInfo(
            current_version_count=len(versions),
            max_versions=10,
            can_create_new_version=len(versions) < 10,
            oldest_version_number=min(v.version_number for v in versions) if versions else None,
            latest_version_number=max(v.version_number for v in versions) if versions else None,
            active_version_number=next((v.version_number for v in versions if v.is_active), None),
        )

    async def compare_versions(
        self,
        db: AsyncSession,
        *,
        user_id: UserId,
        agent_id: AgentId,
        version_a_id: AgentVersionId,
        version_b_id: AgentVersionId,
    ) -> AgentVersionComparisonResponse | None:
        """Compare two versions of an agent.

        Args:
            db: Database session
            user_id: User ID
            agent_id: Agent ID
            version_a_id: First version ID
            version_b_id: Second version ID

        Returns:
            AgentVersionComparisonResponse if successful, None otherwise
        """
        logger.info(f"Comparing versions {version_a_id} and {version_b_id} for agent {agent_id}")

        # Verify agent ownership
        agent = await self.agent_dao.get_by_user_and_id(db, user_id=user_id, agent_id=agent_id)
        if not agent:
            return None

        # Get both versions
        version_a = await self.agent_version_dao.get_with_tools(db, version_id=version_a_id)
        version_b = await self.agent_version_dao.get_with_tools(db, version_id=version_b_id)

        if not version_a or not version_b:
            return None

        # Verify both belong to the same agent
        if version_a.agent_id != agent_id or version_b.agent_id != agent_id:
            return None

        return AgentVersionComparisonResponse.compare_versions(version_a, version_b)

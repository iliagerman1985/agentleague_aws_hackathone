"""Refactored agent service for core agent operations."""

import time
from typing import Any

from game_api import GameType
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.state_chat import StateChatRequest
from app.services.agent_iteration_service import AgentIterationService
from app.services.agent_prompt_service import AgentPromptService
from app.services.agent_test_service import AgentTestService
from app.services.agent_version_service import AgentVersionService
from app.services.game_env_registry import GameEnvRegistry
from app.services.llm_integration_service import LLMIntegrationService
from common.core.guardrails_service import GuardrailsService
from common.core.litellm_schemas import ChatMessage, MessageRole
from common.core.litellm_service import LiteLLMService
from common.enums import LLMProvider
from common.ids import AgentId, AgentVersionId, TestScenarioId, UserId
from common.types import AgentReasoning
from common.utils.utils import get_logger
from shared_db.crud.agent import AgentDAO, AgentStatisticsDAO
from shared_db.schemas.agent import (
    AgentCreate,
    AgentResponse,
    AgentStatisticsResponse,
    AgentTestJsonResult,
    AgentTestRequest,
    AgentTestResponse,
    AgentUpdate,
    AgentVersionComparisonResponse,
    AgentVersionCreate,
    AgentVersionLimitInfo,
    AgentVersionResponse,
    AgentVersionUpdate,
    PromptValidationResult,
    StateGenerationRequest,
    StateGenerationResponse,
    TestDataGenerationResult,
    TestScenarioCreate,
    TestScenarioResponse,
    TestScenarioResultCreate,
    TestScenarioResultResponse,
    TestScenarioUpdate,
)
from shared_db.schemas.game_environments import ToolCallParameters

logger = get_logger(__name__)


class AgentService:
    """Refactored service layer for core agent operations.
    Delegates specialized operations to dedicated services.
    """

    def __init__(
        self,
        agent_dao: AgentDAO,
        agent_statistics_dao: AgentStatisticsDAO,
        llm_integration_service: LLMIntegrationService,
        llm_service: LiteLLMService,
        # Specialized services
        agent_version_service: AgentVersionService,
        agent_test_service: AgentTestService,
        agent_prompt_service: AgentPromptService,
        agent_iteration_service: AgentIterationService,
        guardrails_service: GuardrailsService,
    ) -> None:
        """Initialize AgentService with DAO and service dependencies.

        Args:
            agent_dao: AgentDAO instance for agent operations
            agent_statistics_dao: AgentStatisticsDAO instance for statistics operations
            llm_integration_service: LLMIntegrationService instance for LLM operations
            llm_service: LiteLLMService instance for LLM API calls
            agent_version_service: Service for version management
            agent_test_service: Service for testing operations
            agent_prompt_service: Service for prompt management
            agent_iteration_service: Service for iteration management
            guardrails_service: GuardrailsService instance for content validation
        """
        self.agent_dao = agent_dao
        self.agent_statistics_dao = agent_statistics_dao
        self.llm_integration_service = llm_integration_service
        self.llm_service = llm_service

        # Specialized services
        self.version_service = agent_version_service
        self.test_service = agent_test_service
        self.prompt_service = agent_prompt_service
        self.iteration_service = agent_iteration_service
        self.guardrails_service = guardrails_service

    # Core Agent Operations
    async def get_user_agents(
        self,
        db: AsyncSession,
        *,
        user_id: UserId,
        game_environment: GameType | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AgentResponse]:
        """Get all agents for a user, optionally filtered by game environment.

        Args:
            db: Database session
            user_id: User ID
            game_environment: Optional game environment filter
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of AgentResponse objects
        """
        logger.info(f"Getting agents for user {user_id}, game_environment={game_environment}")

        if game_environment:
            return await self.agent_dao.get_by_user_and_game(db, user_id=user_id, game_environment=game_environment, skip=skip, limit=limit)
        return await self.agent_dao.get_by_user(db, user_id=user_id, skip=skip, limit=limit)

    async def get_user_agent_by_id(
        self,
        db: AsyncSession,
        *,
        user_id: UserId,
        agent_id: AgentId,
    ) -> AgentResponse | None:
        """Get a specific agent for a user.

        Args:
            db: Database session
            user_id: User ID
            agent_id: Agent ID

        Returns:
            AgentResponse if found and owned by user, None otherwise
        """
        logger.info(f"Getting agent {agent_id} for user {user_id}")
        return await self.agent_dao.get_by_user_and_id(db, user_id=user_id, agent_id=agent_id)

    async def create_agent(
        self,
        db: AsyncSession,
        *,
        user_id: UserId,
        agent_in: AgentCreate,
    ) -> AgentResponse:
        """Create a new agent for a user.

        Args:
            db: Database session
            user_id: User ID
            agent_in: Agent creation data

        Returns:
            Created AgentResponse
        """
        logger.info(f"Creating agent for user {user_id}: {agent_in.name}")
        return await self.agent_dao.create(db, obj_in=agent_in, user_id=user_id)

    async def update_agent(
        self,
        db: AsyncSession,
        *,
        user_id: UserId,
        agent_id: AgentId,
        agent_in: AgentUpdate,
    ) -> AgentResponse | None:
        """Update an existing agent.

        Args:
            db: Database session
            user_id: User ID
            agent_id: Agent ID
            agent_in: Agent update data

        Returns:
            Updated AgentResponse if found and owned by user, None otherwise
        """
        logger.info(f"Updating agent {agent_id} for user {user_id}")

        # Get the agent first to verify ownership
        agent = await self.agent_dao.get_by_user_and_id(db, user_id=user_id, agent_id=agent_id)
        if not agent:
            return None

        # Use DAO to update (DAO will fetch the SQLAlchemy model internally)
        return await self.agent_dao.update_by_id(db, id=agent_id, obj_in=agent_in)

    async def delete_agent(
        self,
        db: AsyncSession,
        *,
        user_id: UserId,
        agent_id: AgentId,
    ) -> bool:
        """Delete an agent and all its versions.

        Args:
            db: Database session
            user_id: User ID
            agent_id: Agent ID

        Returns:
            True if deleted, False if not found or not owned by user
        """
        logger.info(f"Deleting agent {agent_id} for user {user_id}")

        # Verify ownership before deleting
        agent = await self.agent_dao.get_by_user_and_id(db, user_id=user_id, agent_id=agent_id)
        if not agent:
            return False

        return await self.agent_dao.delete(db, id=agent_id)

    async def clone_agent(
        self,
        db: AsyncSession,
        *,
        user_id: UserId,
        agent_id: AgentId,
    ) -> AgentResponse | None:
        """Clone an agent (typically a system agent) for a user.

        Creates a copy of the agent and its active version owned by the user.

        Args:
            db: Database session
            user_id: User ID
            agent_id: Agent ID to clone

        Returns:
            Cloned AgentResponse if successful, None if source agent not found
        """
        logger.info(f"Cloning agent {agent_id} for user {user_id}")
        return await self.agent_dao.clone_agent(db, agent_id=agent_id, user_id=user_id)

    # Statistics Operations
    async def get_agent_statistics(
        self,
        db: AsyncSession,
        *,
        user_id: UserId,
        agent_id: AgentId,
    ) -> AgentStatisticsResponse | None:
        """Get statistics for an agent.

        Args:
            db: Database session
            user_id: User ID
            agent_id: Agent ID

        Returns:
            AgentStatisticsResponse if found, None otherwise
        """
        logger.info(f"Getting statistics for agent {agent_id}")

        # Verify agent ownership
        agent = await self.agent_dao.get_by_user_and_id(db, user_id=user_id, agent_id=agent_id)
        if not agent:
            return None

        return await self.agent_statistics_dao.get_by_agent(db, agent_id=agent_id)

    async def update_agent_statistics(
        self,
        db: AsyncSession,
        *,
        user_id: UserId,
        agent_id: AgentId,
        updates: dict[str, Any],
    ) -> AgentStatisticsResponse | None:
        """Update statistics for an agent.

        Args:
            db: Database session
            user_id: User ID
            agent_id: Agent ID
            updates: Dictionary of statistics updates

        Returns:
            Updated AgentStatisticsResponse if successful, None otherwise
        """
        logger.info(f"Updating statistics for agent {agent_id}")

        # Verify agent ownership
        agent = await self.agent_dao.get_by_user_and_id(db, user_id=user_id, agent_id=agent_id)
        if not agent:
            return None

        return await self.agent_statistics_dao.update_statistics(db, agent_id=agent_id, updates=updates)

    # Delegation methods for version operations
    async def get_agent_versions(self, db: AsyncSession, *, user_id: UserId, agent_id: AgentId, skip: int = 0, limit: int = 100) -> list[AgentVersionResponse]:
        """Delegate to version service."""
        return await self.version_service.get_agent_versions(db, user_id=user_id, agent_id=agent_id, skip=skip, limit=limit)

    async def get_active_version(self, db: AsyncSession, *, user_id: UserId, agent_id: AgentId) -> AgentVersionResponse | None:
        """Delegate to version service."""
        return await self.version_service.get_active_version(db, user_id=user_id, agent_id=agent_id)

    async def create_version(self, db: AsyncSession, *, user_id: UserId, agent_id: AgentId, version_in: AgentVersionCreate) -> AgentVersionResponse | None:
        """Delegate to version service."""
        return await self.version_service.create_version(db, user_id=user_id, agent_id=agent_id, version_in=version_in)

    async def update_version(
        self, db: AsyncSession, *, user_id: UserId, agent_id: AgentId, version_id: AgentVersionId, version_in: AgentVersionUpdate
    ) -> AgentVersionResponse | None:
        """Delegate to version service."""
        return await self.version_service.update_version(db, user_id=user_id, agent_id=agent_id, version_id=version_id, version_in=version_in)

    async def activate_version(self, db: AsyncSession, *, user_id: UserId, agent_id: AgentId, version_id: AgentVersionId) -> AgentVersionResponse | None:
        """Delegate to version service."""
        return await self.version_service.activate_version(db, user_id=user_id, agent_id=agent_id, version_id=version_id)

    async def get_version_limit_info(self, db: AsyncSession, *, user_id: UserId, agent_id: AgentId) -> AgentVersionLimitInfo | None:
        """Delegate to version service."""
        return await self.version_service.get_version_limit_info(db, user_id=user_id, agent_id=agent_id)

    async def compare_versions(
        self, db: AsyncSession, *, user_id: UserId, agent_id: AgentId, version_a_id: AgentVersionId, version_b_id: AgentVersionId
    ) -> AgentVersionComparisonResponse | None:
        """Delegate to version service."""
        return await self.version_service.compare_versions(db, user_id=user_id, agent_id=agent_id, version_a_id=version_a_id, version_b_id=version_b_id)

    # Delegation methods for test operations
    async def get_test_scenarios(
        self,
        db: AsyncSession,
        *,
        user_id: UserId,
        environment: GameType | None = None,
        agent_id: AgentId | None = None,
        include_system: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> list[TestScenarioResponse]:
        """Delegate to test service."""
        return await self.test_service.get_test_scenarios(
            db, user_id=user_id, environment=environment, agent_id=agent_id, include_system=include_system, skip=skip, limit=limit
        )

    async def create_test_scenario(self, db: AsyncSession, *, user_id: UserId, scenario_in: TestScenarioCreate) -> TestScenarioResponse:
        """Delegate to test service."""
        return await self.test_service.create_test_scenario(db, user_id=user_id, scenario_in=scenario_in)

    async def get_test_scenario(self, db: AsyncSession, *, user_id: UserId, scenario_id: TestScenarioId) -> TestScenarioResponse | None:
        """Delegate to test service."""
        return await self.test_service.get_test_scenario(db, user_id=user_id, scenario_id=scenario_id)

    async def update_test_scenario(
        self, db: AsyncSession, *, user_id: UserId, scenario_id: TestScenarioId, scenario_in: TestScenarioUpdate
    ) -> TestScenarioResponse | None:
        """Delegate to test service."""
        return await self.test_service.update_test_scenario(db, user_id=user_id, scenario_id=scenario_id, scenario_in=scenario_in)

    async def create_test_result(self, db: AsyncSession, *, user_id: UserId, result_in: TestScenarioResultCreate) -> TestScenarioResultResponse | None:
        """Delegate to test service."""
        return await self.test_service.create_test_result(db, user_id=user_id, result_in=result_in)

    async def get_test_results(
        self, db: AsyncSession, *, user_id: UserId, scenario_id: TestScenarioId, skip: int = 0, limit: int = 100
    ) -> list[TestScenarioResultResponse]:
        """Delegate to test service."""
        return await self.test_service.get_test_results(db, user_id=user_id, scenario_id=scenario_id, skip=skip, limit=limit)

    async def delete_test_scenario(self, db: AsyncSession, user_id: UserId, scenario_id: TestScenarioId) -> bool:
        """Delegate to test service."""
        return await self.test_service.delete_test_scenario(db, user_id=user_id, scenario_id=scenario_id)

    async def save_game_state_as_scenario(
        self,
        db: AsyncSession,
        *,
        user_id: UserId,
        agent_id: AgentId,
        name: str,
        description: str | None,
        game_state: dict[str, Any],
        tags: list[str] | None = None,
    ) -> TestScenarioResponse:
        """Delegate to test service."""
        return await self.test_service.save_game_state_as_scenario(
            db, user_id=user_id, agent_id=agent_id, name=name, description=description, game_state=game_state, tags=tags
        )

    async def get_saved_game_states(
        self,
        db: AsyncSession,
        *,
        user_id: UserId,
        agent_id: AgentId | None = None,
        environment: GameType | None = None,
        tags: list[str] | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[TestScenarioResponse]:
        """Delegate to test service."""
        return await self.test_service.get_saved_game_states(db, user_id=user_id, agent_id=agent_id, environment=environment, tags=tags, skip=skip, limit=limit)

    def generate_test_data(self, instructions: str, environment: GameType) -> TestDataGenerationResult:
        """Delegate to test service."""
        return self.test_service.generate_test_data(instructions, environment)

    async def generate_test_json(self, db: AsyncSession, user_id: UserId, agent_id: AgentId) -> AgentTestJsonResult[Any]:
        """Delegate to test service."""
        return await self.test_service.generate_test_json(db, user_id, agent_id)

    async def generate_state_from_description(
        self, db: AsyncSession, user_id: UserId, agent_id: AgentId, request: StateGenerationRequest
    ) -> StateGenerationResponse:
        """Delegate to test service."""
        return await self.test_service.generate_state_from_description(db, user_id, agent_id, request)

    # Delegation methods for prompt operations
    def validate_prompt(self, prompt: str, environment: GameType) -> PromptValidationResult:
        """Delegate to prompt service."""
        return self.prompt_service.validate_prompt(prompt, environment)

    async def get_state_generation_examples(self, db: AsyncSession, *, user_id: UserId, agent_id: AgentId) -> list[str]:
        """Return environment-specific example prompts for state generation/editing."""
        agent = await self.agent_dao.get_by_user_and_id(db, user_id=user_id, agent_id=agent_id)
        if not agent:
            return []
        env_cls = GameEnvRegistry.instance().get(agent.game_environment)
        try:
            examples = env_cls.get_state_generation_examples()
            return list(examples)
        except Exception:
            return []

    # Delegation methods for streaming operations
    async def stream_state_chat(self, db: AsyncSession, user_id: UserId, agent_id: AgentId, request: StateChatRequest):
        """Delegate to unified AgentTestService for streaming state chat."""
        async for chunk in self.test_service.stream_state_chat(db, user_id, agent_id, request):
            yield chunk

    # Agent Testing Operations (delegated to AgentTestService)
    async def test_agent_iteration(
        self,
        db: AsyncSession,
        *,
        user_id: UserId,
        agent_id: AgentId,
        request: AgentTestRequest,
    ) -> AgentTestResponse:
        """Execute a single agent test iteration with UI-provided parameters.

        Args:
            db: Database session
            user_id: User ID for ownership verification
            agent_id: Agent ID to test
            request: Test request with game state, LLM, and iteration data

        Returns:
            AgentTestResponse with reasoning, action, or tool request
        """
        start_time = time.time()

        try:
            # 1. Fetch agent with full details (including tools)
            agent = await self.agent_dao.get_agent_with_full_details(db, user_id=user_id, agent_id=agent_id)
            if not agent or not agent.active_version:
                return self._create_error_response("Agent not found or has no active version", start_time, "none")

            agent_version = agent.active_version

            # 2. Validate LLM access
            llm_integration = await self.llm_integration_service.get_integration_for_use(db, integration_id=request.llm_integration_id)
            if not llm_integration:
                return self._create_error_response("LLM integration not found or not accessible", start_time, "none")

            # 3. Variable substitution on core prompt
            system_prompt_core = self.prompt_service.substitute_variables(agent_version.system_prompt, request.game_state)
            # Resolve environment-specific decision schema/output type
            env_cls = GameEnvRegistry.instance().get(agent.game_environment)
            types_cls = env_cls.types()
            decision_output_type = types_cls.agent_decision_type()

            # 4. Inject prompt sections (INCLUDING TOOLS)
            system_prompt_with_sections = await self.prompt_service.inject_prompt_sections(
                db,
                version=agent_version,
                core_prompt=system_prompt_core,
                game_state=request.game_state,
                iteration_history=request.iteration_history,
                environment=agent.game_environment,
            )

            # 5. Final variable substitution (on injected sections too)
            system_prompt = self.prompt_service.substitute_variables(system_prompt_with_sections, request.game_state)

            # 6. Create current iteration entries and convert to messages
            current_iterations = self.iteration_service.prepare_current_iterations(
                request.iteration_history, request.game_state, request.tool_result.model_dump() if request.tool_result else None
            )

            # Convert iterations to messages for LLM
            messages = self.iteration_service.iterations_to_messages(current_iterations, system_prompt)

            # Add conversation instructions if present
            if agent_version.conversation_instructions:
                instructions = self.prompt_service.substitute_variables(agent_version.conversation_instructions, request.game_state)
                messages.append({"role": "system", "content": f"Conversation Instructions: {instructions}"})

            # 7. Execute LLM call
            chat_messages = [ChatMessage(role=MessageRole(msg["role"]), content=msg["content"]) for msg in messages]

            # Debug: Log the complete conversation being sent to LLM
            logger.info("=" * 80)
            logger.info("💬 COMPLETE CONVERSATION SENT TO LLM")
            logger.info("=" * 80)
            for i, msg in enumerate(messages, 1):
                logger.info(f"Message {i} ({msg['role'].upper()}):")
                logger.info(f"{msg['content']}")
                logger.info("-" * 40)
            logger.info("=" * 80)

            # 8. Execute agent decision with retry logic for action validation errors
            max_validation_retries = 3
            validation_retry_count = 0
            validation_errors: list[str] = []

            while validation_retry_count <= max_validation_retries:
                # Add validation feedback to messages if this is a retry
                current_messages = chat_messages.copy()
                if validation_retry_count > 0 and validation_errors:
                    validation_feedback = (
                        "Your previous action was invalid. Validation errors:\n"
                        + "\n".join(f"- {error}" for error in validation_errors)
                        + "\n\nPlease choose a valid action from the available moves."
                    )
                    current_messages.append(ChatMessage(role=MessageRole.USER, content=validation_feedback))

                # Call LLM with structured prompt and AgentDecision output
                try:
                    llm_response = await self.llm_service.chat_completion(
                        provider=LLMProvider(llm_integration.provider),
                        model=llm_integration.selected_model,
                        messages=current_messages,
                        api_key=llm_integration.api_key,
                        output_type=decision_output_type,
                        config=None,
                    )
                except Exception as e:
                    # Generic parse/validation failure before AgentDecision could be built:
                    # feed the exact error back to the model and retry
                    feedback = (
                        "Your previous response could not be parsed/validated against the required "
                        "AgentDecision JSON schema. Error:\n"
                        f"{e!s}\n\n"
                        "Return exactly one valid JSON object matching the schema."
                    )
                    chat_messages.append(ChatMessage(role=MessageRole.USER, content=feedback))
                    validation_retry_count += 1
                    if validation_retry_count > max_validation_retries:
                        return self._create_error_response(f"Validation failed: {e!s}", start_time, "none")
                    continue

                # Handle the response - AgentDecision is already parsed by LiteLLMService
                execution_time_ms = int((time.time() - start_time) * 1000)

                # Extract the AgentDecision from the LLM response (already parsed)
                response = llm_response.content

                # Check if response is None
                if response is None:
                    return self._create_error_response("LLM returned empty response", start_time, llm_response.model)

                # Response is already an AgentDecision object
                # Create tool request if agent wants to call a tool
                tool_request = None
                if response.tool_call is not None:
                    from shared_db.schemas.agent import ToolCallRequest

                    # Create tool request with raw parameters from the agent decision
                    # Resolve tool_id from the active version's tools for robust lookup on the client
                    tool_id_val = None
                    try:
                        from sqlalchemy import select

                        from shared_db.models.tool import Tool as ToolModel

                        version_tool_ids = agent_version.tool_ids or []
                        if version_tool_ids:
                            res = await db.execute(select(ToolModel.id, ToolModel.name).where(ToolModel.id.in_(version_tool_ids)))
                            name_to_id = {str(name).strip().lower(): _id for (_id, name) in res.all()}
                            tool_id_val = name_to_id.get(str(response.tool_call.tool_name).strip().lower())
                    except Exception:
                        tool_id_val = None

                    tool_request = ToolCallRequest(
                        tool_id=tool_id_val,
                        tool_name=response.tool_call.tool_name,
                        parameters=ToolCallParameters(**response.tool_call.parameters) if response.tool_call.parameters else ToolCallParameters(),
                    )

                # Determine if this is a final response
                is_final = (tool_request is None and response.move is not None) or (response.exit is True)

                # Validate final action if this is a final response
                current_validation_errors: list[str] = []
                if is_final and response.move is not None:
                    logger.info(f"validating final action: {response.move}")
                    # Extract possible moves from game state
                    possible_moves = request.game_state.get("possible_moves")
                    logger.info(f"possible moves from game state: {possible_moves}")
                    if possible_moves is not None:
                        # Convert possible_moves dict to appropriate Pydantic model using env types
                        try:
                            env_cls = GameEnvRegistry.instance().get(agent.game_environment)
                            types_cls = env_cls.types()
                            pm_type = types_cls.possible_moves_type()
                            possible_moves_obj = pm_type.model_validate(possible_moves)
                            logger.info(f"parsed possible moves: {possible_moves_obj}")

                            # Delegate validation to the environment
                            try:
                                current_validation_errors = env_cls.validate_final_action(response.move, possible_moves_obj)
                            except Exception:
                                logger.exception("Environment validate_final_action raised")
                                current_validation_errors = ["Environment validation failed"]
                        except Exception as e:
                            logger.exception("Error parsing possible moves for validation")
                            current_validation_errors = [f"Could not parse possible moves: {e!s}"]
                    else:
                        logger.warning("no possible moves provided - skipping validation")

                # If validation passed or this is not a final response, return success
                if not current_validation_errors or not is_final:
                    # Create AgentTestResponse directly from AgentDecision
                    logger.info(f"creating response with action: {response.move}, exit: {response.exit}")
                    agent_response = AgentTestResponse(
                        reasoning=response.reasoning,
                        action=response.move,
                        tool_request=tool_request,
                        validation_errors=current_validation_errors,
                        execution_time_ms=execution_time_ms,
                        model_used=llm_response.model,
                        is_final=is_final,
                    )

                    # Success - return the response
                    return agent_response

                # Validation failed - prepare for retry
                validation_errors = current_validation_errors
                validation_retry_count += 1

                logger.warning(f"Action validation failed (attempt {validation_retry_count}/{max_validation_retries + 1}): {validation_errors}")

                # If we've exhausted retries, return the failed response
                if validation_retry_count > max_validation_retries:
                    logger.info(f"creating failed response with action: {response.move} and validation errors: {validation_errors}")
                    agent_response = AgentTestResponse(
                        reasoning=response.reasoning,
                        action=response.move,
                        tool_request=tool_request,
                        validation_errors=validation_errors,
                        execution_time_ms=execution_time_ms,
                        model_used=llm_response.model,
                        is_final=is_final,
                    )

                    return agent_response

                # Continue to next retry iteration

            # This should never be reached due to the retry logic, but add fallback
            return self._create_error_response("Unexpected end of retry loop", start_time, llm_integration.selected_model)

        except Exception as e:
            logger.exception("Error during agent test iteration")
            return self._create_error_response(f"Error during execution: {e!s}", start_time, "none")

    def _create_error_response(self, error_message: str, start_time: float, model_used: str) -> AgentTestResponse:
        """Create an error response for agent testing."""
        execution_time_ms = int((time.time() - start_time) * 1000)
        return AgentTestResponse(
            reasoning=AgentReasoning(f"Error: {error_message}"),
            action=None,
            tool_request=None,
            validation_errors=[error_message],
            execution_time_ms=execution_time_ms,
            model_used=model_used,
            is_final=False,
        )

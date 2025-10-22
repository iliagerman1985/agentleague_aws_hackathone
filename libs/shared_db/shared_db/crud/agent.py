"""Agent CRUD operations with async support."""

from datetime import UTC, datetime
from typing import Any, cast

from game_api import GameType
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from common.core.app_error import Errors
from common.ids import (
    AgentExecutionSessionId,
    AgentId,
    AgentIterationHistoryId,
    AgentStatisticsId,
    AgentVersionId,
    TestScenarioId,
    UserId,
)
from shared_db.models.agent import (
    Agent,
    AgentExecutionSession,
    AgentIterationHistory,
    AgentStatistics,
    AgentVersion,
    AgentVersionTool,
    TestScenario,
    TestScenarioResult,
)
from shared_db.models.tool import Tool
from shared_db.schemas.agent import (
    AgentCreate,
    AgentExecutionSessionCreate,
    AgentExecutionSessionResponse,
    AgentFullDetailsResponse,
    AgentIterationHistoryCreate,
    AgentIterationHistoryResponse,
    AgentResponse,
    AgentStatisticsResponse,
    AgentUpdate,
    AgentVersionCreate,
    AgentVersionResponse,
    AgentVersionUpdate,
    TestScenarioCreate,
    TestScenarioResponse,
    TestScenarioResultCreate,
    TestScenarioResultResponse,
    TestScenarioUpdate,
)


class AgentDAO:
    """Data Access Object for Agent operations with async support."""

    def __init__(self) -> None:
        pass

    async def get(self, db: AsyncSession, id: AgentId) -> AgentResponse | None:
        """Get an agent by ID."""
        result = await db.execute(select(Agent).where(Agent.id == id))
        agent = result.scalar_one_or_none()
        return AgentResponse.model_validate(agent) if agent else None

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AgentResponse]:
        """Get multiple agents with pagination."""
        result = await db.execute(select(Agent).offset(skip).limit(limit))
        agents = result.scalars().all()
        return [AgentResponse.model_validate(agent) for agent in agents]

    async def get_by_user(
        self,
        db: AsyncSession,
        *,
        user_id: UserId,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AgentResponse]:
        """Get agents for a specific user with pagination, including system agents."""
        result = await db.execute(
            select(Agent).where(((Agent.user_id == user_id) | Agent.is_system), ~Agent.is_archived).order_by(Agent.updated_at.desc()).offset(skip).limit(limit)
        )
        agents = result.scalars().all()
        return [AgentResponse.model_validate(agent) for agent in agents]

    async def get_by_user_and_id(
        self,
        db: AsyncSession,
        *,
        user_id: UserId,
        agent_id: AgentId,
    ) -> AgentResponse | None:
        """Get a specific agent for a user, including system agents."""
        result = await db.execute(select(Agent).where(Agent.id == agent_id, ((Agent.user_id == user_id) | Agent.is_system), ~Agent.is_archived))
        agent = result.scalar_one_or_none()
        return AgentResponse.model_validate(agent) if agent else None

    async def get_by_user_and_game(
        self,
        db: AsyncSession,
        *,
        user_id: UserId,
        game_environment: GameType,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AgentResponse]:
        """Get agents for a specific user and game environment, including system agents."""
        result = await db.execute(
            select(Agent)
            .where(
                ((Agent.user_id == user_id) | Agent.is_system),
                Agent.game_environment == game_environment,
                ~Agent.is_archived,
            )
            .order_by(Agent.updated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        agents = result.scalars().all()
        return [AgentResponse.model_validate(agent) for agent in agents]

    async def get_agent_with_full_details(
        self,
        db: AsyncSession,
        *,
        user_id: UserId,
        agent_id: AgentId,
    ) -> AgentFullDetailsResponse | None:
        """Get agent with full details including active version and tools."""
        result = await db.execute(
            select(Agent)
            .options(
                joinedload(Agent.versions).joinedload(AgentVersion.tools),
            )
            .where(Agent.id == agent_id, Agent.user_id == user_id)
        )
        agent = result.unique().scalar_one_or_none()

        if not agent:
            return None

        # Convert to response schema
        agent_response = AgentResponse.model_validate(agent)

        # Find active version
        active_version = None
        for version in agent.versions:
            if version.is_active:
                # Convert version with tools
                version_response = AgentVersionResponse.model_validate(version)
                version_response.tool_ids = [tool.tool_id for tool in version.tools]
                active_version = version_response
                break

        # Create full details response
        return AgentFullDetailsResponse(**agent_response.model_dump(), active_version=active_version, total_versions=len(agent.versions))

    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: AgentCreate,
        user_id: UserId | None = None,
        **kwargs: Any,
    ) -> AgentResponse:
        """Create a new agent."""
        if user_id is None:
            raise ValueError("user_id is required")

        agent = Agent(
            user_id=user_id,
            name=obj_in.name,
            description=obj_in.description,
            game_environment=obj_in.game_environment,
            auto_buy=obj_in.auto_buy,
            is_active=obj_in.is_active,
        )
        db.add(agent)
        await db.commit()
        await db.refresh(agent)

        # Return directly from ORM using Pydantic to avoid missing fields
        return AgentResponse.model_validate(agent)

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: Agent,
        obj_in: AgentUpdate,
    ) -> AgentResponse:
        """Update an existing agent.

        System agents (is_system=True, user_id=None) cannot be updated.
        """
        # Prevent updating system agents
        if db_obj.is_system:
            raise ValueError("Cannot update system agents")

        update_data = obj_in.model_dump(exclude_unset=True)

        # Prevent updating game_environment (immutable)
        update_data.pop("game_environment", None)

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        await db.commit()
        await db.refresh(db_obj)
        return AgentResponse.model_validate(db_obj)

    async def update_by_id(
        self,
        db: AsyncSession,
        *,
        id: AgentId,
        obj_in: AgentUpdate,
    ) -> AgentResponse | None:
        """Update an agent by ID."""
        result = await db.execute(select(Agent).where(Agent.id == id))
        agent = result.scalar_one_or_none()
        if not agent:
            return None
        return await self.update(db, db_obj=agent, obj_in=obj_in)

    async def delete(self, db: AsyncSession, *, id: AgentId) -> bool:
        """Soft-archive an agent by ID.

        Instead of hard-deleting (which can violate FKs with game_players), we mark the
        agent as archived and inactive, and set archived_at.
        """
        result = await db.execute(select(Agent).where(Agent.id == id))
        agent = result.scalar_one_or_none()
        if not agent:
            return False

        agent.is_archived = True
        agent.is_active = False
        agent.archived_at = datetime.now(UTC)

        await db.commit()
        await db.refresh(agent)
        return True

    async def clone_agent(
        self,
        db: AsyncSession,
        *,
        agent_id: AgentId,
        user_id: UserId,
    ) -> AgentResponse | None:
        """Clone an agent (typically a system agent) for a specific user.

        Creates a copy of the agent with the new user_id and is_system=False.
        The cloned agent will have " (Copy)" appended to its name.
        Also clones the active version if one exists.

        Args:
            db: Database session
            agent_id: ID of the agent to clone
            user_id: ID of the user who will own the clone

        Returns:
            AgentResponse of the cloned agent, or None if source agent not found
        """
        # Get the source agent with its versions
        result = await db.execute(select(Agent).options(selectinload(Agent.versions).selectinload(AgentVersion.tools)).where(Agent.id == agent_id))
        source_agent = result.unique().scalar_one_or_none()
        if source_agent is None:
            return None

        # Create a new agent with copied data
        cloned_agent = Agent(
            user_id=user_id,
            name=f"{source_agent.name} (Copy)",
            description=source_agent.description,
            game_environment=source_agent.game_environment,
            auto_buy=source_agent.auto_buy,
            is_active=source_agent.is_active,
            is_system=False,  # Cloned agents are never system agents
        )
        db.add(cloned_agent)
        await db.flush()  # Flush to get the agent ID

        # Clone the active version if it exists
        active_version = None
        for version in source_agent.versions:
            if version.is_active:
                active_version = version
                break

        if active_version:
            # Create a new version with copied data
            cloned_version = AgentVersion(
                agent_id=cloned_agent.id,
                user_id=user_id,  # Set the user_id for the cloned version
                version_number=1,  # First version for the cloned agent
                system_prompt=active_version.system_prompt,
                conversation_instructions=active_version.conversation_instructions,
                exit_criteria=active_version.exit_criteria,
                slow_llm_provider=active_version.slow_llm_provider,
                fast_llm_provider=active_version.fast_llm_provider,
                slow_llm_model=active_version.slow_llm_model,
                fast_llm_model=active_version.fast_llm_model,
                timeout=active_version.timeout,
                max_iterations=active_version.max_iterations,
                is_active=True,
            )
            db.add(cloned_version)
            await db.flush()  # Flush to get the version ID

            # Clone the tool associations
            tools = cast(list[AgentVersionTool], (active_version.tools or []))
            for tool_assoc in tools:
                cloned_tool_assoc = AgentVersionTool(
                    agent_version_id=cloned_version.id,
                    tool_id=tool_assoc.tool_id,
                    order=tool_assoc.order,
                )
                db.add(cloned_tool_assoc)

        await db.commit()
        await db.refresh(cloned_agent)
        return AgentResponse.model_validate(cloned_agent)


class AgentVersionDAO:
    """Data Access Object for AgentVersion operations with async support."""

    def __init__(self) -> None:
        pass

    async def get(self, db: AsyncSession, id: AgentVersionId) -> AgentVersionResponse | None:
        """Get an agent version by ID including tool IDs and agent."""
        result = await db.execute(select(AgentVersion).options(selectinload(AgentVersion.tools), joinedload(AgentVersion.agent)).where(AgentVersion.id == id))
        version = result.unique().scalar_one_or_none()
        if not version:
            return None
        response = AgentVersionResponse.model_validate(version)
        # Populate tool_ids from association table with explicit typing
        try:
            tools = cast(list[AgentVersionTool], (version.tools or []))
            response.tool_ids = [t.tool_id for t in tools]
        except Exception:
            response.tool_ids = []
        # Populate game_environment from parent agent
        if version.agent:
            response.game_environment = version.agent.game_environment
        return response

    async def get_or_throw(self, db: AsyncSession, id: AgentVersionId) -> AgentVersionResponse:
        """Get an agent version by ID including tool IDs, throw if not found."""
        version = await self.get(db, id)
        if not version:
            raise Errors.Agent.NOT_FOUND.create(message=f"Agent version not found: {id}", details={"version_id": id})
        return version

    async def get_by_ids(self, db: AsyncSession, ids: set[AgentVersionId]) -> dict[AgentVersionId, AgentVersion]:
        """Get multiple agent versions by IDs including tool IDs and agent."""
        result = await db.execute(
            select(AgentVersion).options(selectinload(AgentVersion.tools), joinedload(AgentVersion.agent)).where(AgentVersion.id.in_(ids))
        )
        versions = result.scalars().all()

        responses: dict[AgentVersionId, AgentVersion] = {}
        for version in versions:
            responses[version.id] = version

        return responses

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AgentVersionResponse]:
        """Get multiple agent versions with pagination."""
        result = await db.execute(select(AgentVersion).offset(skip).limit(limit))
        versions = result.scalars().all()
        return [AgentVersionResponse.model_validate(version) for version in versions]

    async def get_with_tools(self, db: AsyncSession, version_id: AgentVersionId) -> AgentVersionResponse | None:
        """Get an agent version with its tools loaded."""
        result = await db.execute(
            select(AgentVersion).options(joinedload(AgentVersion.tools).joinedload(AgentVersionTool.tool)).where(AgentVersion.id == version_id)
        )
        version = result.unique().scalar_one_or_none()

        if not version:
            return None

        response = AgentVersionResponse.model_validate(version)
        # Add tool information
        tools = cast(list[AgentVersionTool], (version.tools or []))
        response.tool_ids = [vt.tool_id for vt in sorted(tools, key=lambda x: x.order)]
        return response

    async def get_by_agent(
        self,
        db: AsyncSession,
        *,
        agent_id: AgentId,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AgentVersionResponse]:
        """Get all versions for an agent including tool IDs."""
        result = await db.execute(
            select(AgentVersion)
            .options(joinedload(AgentVersion.tools))
            .where(AgentVersion.agent_id == agent_id)
            .order_by(AgentVersion.version_number.desc())
            .offset(skip)
            .limit(limit)
        )
        versions = result.unique().scalars().all()
        responses: list[AgentVersionResponse] = []
        for version in versions:
            resp = AgentVersionResponse.model_validate(version)
            try:
                tools = cast(list[AgentVersionTool], (version.tools or []))
                resp.tool_ids = [vt.tool_id for vt in sorted(tools, key=lambda x: x.order)]
            except Exception:
                resp.tool_ids = []
            responses.append(resp)
        return responses

    async def get_active_version(self, db: AsyncSession, agent_id: AgentId) -> AgentVersionResponse | None:
        """Get the active version for an agent."""
        result = await db.execute(
            select(AgentVersion)
            .options(joinedload(AgentVersion.tools))
            .where(
                AgentVersion.agent_id == agent_id,
                AgentVersion.is_active,
            )
        )
        version = result.unique().scalar_one_or_none()
        if not version:
            return None
        response = AgentVersionResponse.model_validate(version)
        tools = cast(list[AgentVersionTool], (version.tools or []))
        response.tool_ids = [vt.tool_id for vt in sorted(tools, key=lambda x: x.order)]
        return response

    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: AgentVersionCreate,
        agent_id: AgentId | None = None,
        user_id: UserId | None = None,
        **kwargs: Any,
    ) -> AgentVersionResponse:
        """Create a new agent version."""
        if agent_id is None:
            raise ValueError("agent_id is required")
        if user_id is None:
            raise ValueError("user_id is required")

        # Get the next version number
        result = await db.execute(select(func.max(AgentVersion.version_number)).where(AgentVersion.agent_id == agent_id))
        max_version = result.scalar()
        next_version = (max_version or 0) + 1

        # Check if we need to delete old versions (max 10)
        if next_version > 10:
            # Delete the oldest version
            result = await db.execute(select(AgentVersion).where(AgentVersion.agent_id == agent_id).order_by(AgentVersion.version_number))
            oldest_version = result.scalar_one_or_none()
            if oldest_version:
                await db.delete(oldest_version)
                await db.flush()

        # Deactivate current active version
        _ = await db.execute(
            update(AgentVersion)
            .where(
                AgentVersion.agent_id == agent_id,
                AgentVersion.is_active,
            )
            .values(is_active=False)
        )

        # Create new version
        version = AgentVersion(
            agent_id=agent_id,
            user_id=user_id,
            version_number=next_version,
            system_prompt=obj_in.system_prompt,
            conversation_instructions=obj_in.conversation_instructions,
            exit_criteria=obj_in.exit_criteria,
            slow_llm_provider=str(obj_in.slow_llm_provider),
            fast_llm_provider=str(obj_in.fast_llm_provider),
            slow_llm_model=obj_in.slow_llm_model,
            fast_llm_model=obj_in.fast_llm_model,
            timeout=obj_in.timeout,
            max_iterations=obj_in.max_iterations,
            is_active=True,
        )
        db.add(version)
        await db.flush()

        # Add tool associations
        if obj_in.tool_ids:
            for order, tool_id in enumerate(obj_in.tool_ids):
                # Verify tool exists
                result = await db.execute(select(Tool).where(Tool.id == tool_id))
                tool = result.scalar_one_or_none()
                if tool:
                    version_tool = AgentVersionTool(
                        agent_version_id=version.id,
                        tool_id=tool_id,
                        order=order,
                    )
                    db.add(version_tool)

        await db.commit()
        await db.refresh(version)

        response = AgentVersionResponse.model_validate(version)
        response.tool_ids = obj_in.tool_ids or []
        return response

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: AgentVersion,
        obj_in: AgentVersionUpdate,
    ) -> AgentVersionResponse:
        """Update an existing agent version."""
        update_data = obj_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        await db.commit()
        await db.refresh(db_obj)
        response = AgentVersionResponse.model_validate(db_obj)
        try:
            tools = cast(list[AgentVersionTool], (db_obj.tools or []))
            response.tool_ids = [t.tool_id for t in tools]
        except Exception:
            response.tool_ids = []
        return response

    async def update_by_id(
        self,
        db: AsyncSession,
        *,
        id: AgentVersionId,
        obj_in: AgentVersionUpdate,
    ) -> AgentVersionResponse | None:
        """Update an agent version by ID."""
        # Load the version with tools relationship to avoid lazy loading issues
        result = await db.execute(select(AgentVersion).options(joinedload(AgentVersion.tools)).where(AgentVersion.id == id))
        version = result.unique().scalar_one_or_none()
        if not version:
            return None
        return await self.update(db, db_obj=version, obj_in=obj_in)

    async def activate(self, db: AsyncSession, version_id: AgentVersionId) -> AgentVersionResponse | None:
        """Activate a specific version and deactivate others."""
        result = await db.execute(select(AgentVersion).where(AgentVersion.id == version_id))
        version = result.scalar_one_or_none()
        if not version:
            return None

        # Deactivate all other versions
        _ = await db.execute(
            update(AgentVersion)
            .where(
                AgentVersion.agent_id == version.agent_id,
                AgentVersion.id != version_id,
            )
            .values(is_active=False)
        )

        # Activate this version
        _ = await db.execute(update(AgentVersion).where(AgentVersion.id == version_id).values(is_active=True))
        await db.commit()
        await db.refresh(version)

        return AgentVersionResponse.model_validate(version)

    async def delete(self, db: AsyncSession, *, id: AgentVersionId) -> bool:
        """Delete an agent version."""
        result = await db.execute(select(AgentVersion).where(AgentVersion.id == id))
        version = result.scalar_one_or_none()
        if version:
            await db.delete(version)
            await db.commit()
            return True
        return False

    async def find_system_agents(
        self,
        db: AsyncSession,
        game_type: GameType,
        limit: int = 10,
    ) -> list[AgentVersionResponse]:
        """Find active system agents for a specific game type.

        Args:
            db: Database session
            game_type: Game type to find agents for
            limit: Maximum number of agents to return

        Returns:
            List of system agent versions
        """
        result = await db.execute(
            select(AgentVersion)
            .options(
                joinedload(AgentVersion.agent),
                selectinload(AgentVersion.tools),
            )
            .join(Agent, AgentVersion.agent_id == Agent.id)
            .where(
                Agent.is_system.is_(True),
                Agent.game_environment == game_type,
                AgentVersion.is_active.is_(True),
            )
            .limit(limit)
        )
        versions = result.unique().scalars().all()

        responses: list[AgentVersionResponse] = []
        for version in versions:
            resp = AgentVersionResponse.model_validate(version)
            try:
                tools = cast(list[AgentVersionTool], (version.tools or []))
                resp.tool_ids = [vt.tool_id for vt in sorted(tools, key=lambda x: x.order)]
            except Exception:
                resp.tool_ids = []
            responses.append(resp)

        return responses

    async def find_admin_agents_for_matchmaking(
        self,
        db: AsyncSession,
        game_type: GameType,
        admin_user_id: UserId,
        limit: int = 10,
    ) -> list[AgentVersionResponse]:
        """Find active agents owned by admin for matchmaking (Krang, Shredder, etc.).

        Args:
            db: Database session
            game_type: Game type to find agents for
            admin_user_id: Admin user ID
            limit: Maximum number of agents to return

        Returns:
            List of admin agent versions for matchmaking
        """
        result = await db.execute(
            select(AgentVersion)
            .options(
                joinedload(AgentVersion.agent),
                selectinload(AgentVersion.tools),
            )
            .join(Agent, AgentVersion.agent_id == Agent.id)
            .where(
                Agent.user_id == admin_user_id,
                Agent.game_environment == game_type,
                Agent.is_active.is_(True),
                Agent.can_play_in_real_matches.is_(True),  # Filter out playground-only agents
                AgentVersion.is_active.is_(True),
            )
            .limit(limit)
        )
        versions = result.unique().scalars().all()

        responses: list[AgentVersionResponse] = []
        for version in versions:
            resp = AgentVersionResponse.model_validate(version)
            try:
                tools = cast(list[AgentVersionTool], (version.tools or []))
                resp.tool_ids = [vt.tool_id for vt in sorted(tools, key=lambda x: x.order)]
            except Exception:
                resp.tool_ids = []
            responses.append(resp)

        return responses


class TestScenarioDAO:
    """Data Access Object for TestScenario operations with async support."""

    def __init__(self) -> None:
        pass

    async def get(self, db: AsyncSession, id: TestScenarioId) -> TestScenarioResponse | None:
        """Get a test scenario by ID."""
        result = await db.execute(select(TestScenario).where(TestScenario.id == id))
        scenario = result.scalar_one_or_none()
        return TestScenarioResponse.model_validate(scenario) if scenario else None

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[TestScenarioResponse]:
        """Get multiple test scenarios with pagination."""
        result = await db.execute(select(TestScenario).offset(skip).limit(limit))
        scenarios = result.scalars().all()
        return [TestScenarioResponse.model_validate(scenario) for scenario in scenarios]

    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: TestScenarioCreate,
        user_id: UserId | None = None,
        **kwargs: Any,
    ) -> TestScenarioResponse:
        """Create a new test scenario."""
        # For system scenarios, user_id can be None
        if not obj_in.is_system and user_id is None:
            raise ValueError("user_id is required for non-system scenarios")

        scenario = TestScenario(
            user_id=user_id,
            name=obj_in.name,
            description=obj_in.description,
            environment=obj_in.environment,
            game_state=obj_in.game_state,
            tags=obj_in.tags,
            is_system=obj_in.is_system,
        )
        db.add(scenario)
        await db.commit()
        await db.refresh(scenario)
        return TestScenarioResponse.model_validate(scenario)

    async def get_by_user(
        self,
        db: AsyncSession,
        *,
        user_id: UserId,
        environment: GameType | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[TestScenarioResponse]:
        """Get test scenarios for a specific user, including system-wide scenarios."""
        # Get user scenarios OR system scenarios
        query = select(TestScenario).where((TestScenario.user_id == user_id) | TestScenario.is_system)

        if environment is not None:
            query = query.where(TestScenario.environment == environment)

        query = query.order_by(TestScenario.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        scenarios = result.scalars().all()
        return [TestScenarioResponse.model_validate(scenario) for scenario in scenarios]

    async def create_result(
        self,
        db: AsyncSession,
        *,
        obj_in: TestScenarioResultCreate,
    ) -> TestScenarioResultResponse:
        """Create a new test scenario result."""
        result = TestScenarioResult(**obj_in.model_dump())
        db.add(result)
        await db.commit()
        await db.refresh(result)
        return TestScenarioResultResponse.model_validate(result)

    async def get_results(
        self,
        db: AsyncSession,
        *,
        scenario_id: TestScenarioId,
        skip: int = 0,
        limit: int = 100,
    ) -> list[TestScenarioResultResponse]:
        """Get results for a specific test scenario."""
        result = await db.execute(
            select(TestScenarioResult)
            .where(TestScenarioResult.test_scenario_id == scenario_id)
            .order_by(TestScenarioResult.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        results = result.scalars().all()
        return [TestScenarioResultResponse.model_validate(r) for r in results]

    async def delete(self, db: AsyncSession, *, id: TestScenarioId) -> bool:
        """Delete a test scenario by ID."""
        result = await db.execute(select(TestScenario).where(TestScenario.id == id))
        scenario = result.scalar_one_or_none()
        if scenario:
            await db.delete(scenario)
            await db.commit()
            return True
        return False

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: TestScenario,
        obj_in: TestScenarioUpdate,
    ) -> TestScenarioResponse:
        """Update an existing test scenario."""
        update_data = obj_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        await db.commit()
        await db.refresh(db_obj)
        return TestScenarioResponse.model_validate(db_obj)

    async def update_by_id(
        self,
        db: AsyncSession,
        *,
        id: TestScenarioId,
        obj_in: TestScenarioUpdate,
    ) -> TestScenarioResponse | None:
        """Update a test scenario by ID."""
        result = await db.execute(select(TestScenario).where(TestScenario.id == id))
        scenario = result.scalar_one_or_none()
        if not scenario:
            return None
        return await self.update(db, db_obj=scenario, obj_in=obj_in)


class AgentStatisticsDAO:
    """Data Access Object for AgentStatistics operations with async support."""

    def __init__(self) -> None:
        pass

    async def get(self, db: AsyncSession, id: AgentStatisticsId) -> AgentStatisticsResponse | None:
        """Get agent statistics by ID."""
        result = await db.execute(select(AgentStatistics).where(AgentStatistics.id == id))
        stats = result.scalar_one_or_none()
        if not stats:
            return None
        # Convert the statistics JSON to AgentStatisticsData for proper camelCase serialization
        stats_data = stats.get_statistics_data()
        return AgentStatisticsResponse(id=stats.id, agent_id=stats.agent_id, statistics=stats_data, updated_at=stats.updated_at)

    async def get_by_agent(self, db: AsyncSession, agent_id: AgentId) -> AgentStatisticsResponse | None:
        """Get statistics for a specific agent."""
        result = await db.execute(select(AgentStatistics).where(AgentStatistics.agent_id == agent_id))
        stats = result.scalar_one_or_none()
        if not stats:
            return None
        # Convert the statistics JSON to AgentStatisticsData for proper camelCase serialization
        stats_data = stats.get_statistics_data()
        return AgentStatisticsResponse(id=stats.id, agent_id=stats.agent_id, statistics=stats_data, updated_at=stats.updated_at)

    async def update_statistics(
        self,
        db: AsyncSession,
        *,
        agent_id: AgentId,
        updates: dict[str, Any],
    ) -> AgentStatisticsResponse:
        """Update statistics for an agent."""
        result = await db.execute(select(AgentStatistics).where(AgentStatistics.agent_id == agent_id))
        stats = result.scalar_one_or_none()

        if not stats:
            # Create new statistics if they don't exist
            stats = AgentStatistics(agent_id=agent_id)
            # Ensure non-null JSON by setting defaults via model helper
            stats.set_statistics(stats.get_statistics())
            db.add(stats)

        # Update statistics with new values
        current_stats = stats.get_statistics()

        # Debug logging
        from common.core.logging_service import get_logger

        logger = get_logger(__name__)
        logger.info(
            f"Before update - current_stats keys: {list(current_stats.keys())}",
            extra={
                "session_time_seconds": current_stats.get("session_time_seconds"),
                "longest_game_seconds": current_stats.get("longest_game_seconds"),
                "shortest_game_seconds": current_stats.get("shortest_game_seconds"),
            },
        )
        logger.info(
            f"Updates to apply: {list(updates.keys())}",
            extra={
                "session_time_seconds": updates.get("session_time_seconds"),
                "longest_game_seconds": updates.get("longest_game_seconds"),
                "shortest_game_seconds": updates.get("shortest_game_seconds"),
            },
        )

        current_stats.update(updates)

        logger.info(
            f"After update - current_stats keys: {list(current_stats.keys())}",
            extra={
                "session_time_seconds": current_stats.get("session_time_seconds"),
                "longest_game_seconds": current_stats.get("longest_game_seconds"),
                "shortest_game_seconds": current_stats.get("shortest_game_seconds"),
            },
        )

        stats.set_statistics(current_stats)

        # Mark the statistics column as modified so SQLAlchemy knows to update it
        from sqlalchemy.orm import attributes

        attributes.flag_modified(stats, "statistics")

        await db.commit()
        await db.refresh(stats)

        logger.info(
            f"After commit - stats.statistics keys: {list(stats.statistics.keys())}",
            extra={
                "session_time_seconds": stats.statistics.get("session_time_seconds"),
                "longest_game_seconds": stats.statistics.get("longest_game_seconds"),
                "shortest_game_seconds": stats.statistics.get("shortest_game_seconds"),
            },
        )

        # Convert the statistics JSON to AgentStatisticsData for proper camelCase serialization
        stats_data = stats.get_statistics_data()
        return AgentStatisticsResponse(id=stats.id, agent_id=stats.agent_id, statistics=stats_data, updated_at=stats.updated_at)


class AgentExecutionSessionDAO:
    """Data Access Object for AgentExecutionSession operations with async support."""

    def __init__(self) -> None:
        pass

    async def get(self, db: AsyncSession, id: AgentExecutionSessionId) -> AgentExecutionSessionResponse | None:
        """Get an execution session by ID."""
        result = await db.execute(select(AgentExecutionSession).where(AgentExecutionSession.id == id))
        session = result.scalar_one_or_none()
        return AgentExecutionSessionResponse.model_validate(session) if session else None

    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: AgentExecutionSessionCreate,
        **kwargs: Any,
    ) -> AgentExecutionSessionResponse:
        """Create a new execution session."""
        session = AgentExecutionSession(**obj_in.model_dump())
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return AgentExecutionSessionResponse.model_validate(session)


class AgentIterationHistoryDAO:
    """Data Access Object for AgentIterationHistory operations with async support."""

    def __init__(self) -> None:
        pass

    async def get(self, db: AsyncSession, id: AgentIterationHistoryId) -> AgentIterationHistoryResponse | None:
        """Get iteration history by ID."""
        result = await db.execute(select(AgentIterationHistory).where(AgentIterationHistory.id == id))
        history = result.scalar_one_or_none()
        return AgentIterationHistoryResponse.model_validate(history) if history else None

    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: AgentIterationHistoryCreate,
        **kwargs: Any,
    ) -> AgentIterationHistoryResponse:
        """Create a new iteration history record."""
        history = AgentIterationHistory(**obj_in.model_dump())
        db.add(history)
        await db.commit()
        await db.refresh(history)
        return AgentIterationHistoryResponse.model_validate(history)


class TestScenarioResultDAO:
    """Data Access Object for TestScenarioResult operations with async support."""

    def __init__(self) -> None:
        pass

    async def get(self, db: AsyncSession, id: int) -> TestScenarioResultResponse | None:
        """Get test scenario result by ID."""
        result = await db.execute(select(TestScenarioResult).where(TestScenarioResult.id == id))
        scenario_result = result.scalar_one_or_none()
        return TestScenarioResultResponse.model_validate(scenario_result) if scenario_result else None

    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: TestScenarioResultCreate,
        **kwargs: Any,
    ) -> TestScenarioResultResponse:
        """Create a new test scenario result."""
        scenario_result = TestScenarioResult(**obj_in.model_dump())
        db.add(scenario_result)
        await db.commit()
        await db.refresh(scenario_result)
        return TestScenarioResultResponse.model_validate(scenario_result)

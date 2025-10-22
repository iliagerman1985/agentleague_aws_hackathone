"""Agent API routes for managing AI agents."""

import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from game_api import GameType
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_agent_service, get_agent_version_dao, get_current_user, get_db
from app.schemas.agents_metadata import EnvironmentsMetadataResponse
from app.schemas.scoring import (
    AgentProfileData,
    GameRatingUpdateRequest,
    GameRatingUpdateResponse,
)
from app.schemas.state_chat import StateChatRequest
from app.services.agent_service import AgentService
from app.services.game_env_registry import GameEnvRegistry
from app.services.scoring_service import ScoringService
from common.core.logging_service import get_logger
from common.ids import AgentId, AgentVersionId, TestScenarioId, UserId
from shared_db.crud.agent import AgentDAO, AgentStatisticsDAO, AgentVersionDAO
from shared_db.crud.game import GameDAO
from shared_db.crud.llm_usage import LLMUsageDAO
from shared_db.models.agent import Agent, AgentGameRating, AgentStatistics
from shared_db.models.game_enums import GAME_ENVIRONMENT_METADATA as _META
from shared_db.schemas.agent import (
    AgentCreate,
    AgentIdLookupResponse,
    AgentResponse,
    AgentStatisticsResponse,
    AgentTestRequest,
    AgentTestResponse,
    AgentUpdate,
    AgentVersionComparisonResponse,
    AgentVersionCreate,
    AgentVersionLimitInfo,
    AgentVersionResponse,
    AgentVersionUpdate,
    AutocompleteItem,
    GameEnvironmentInfo,
    GameEnvironmentSchema,
    PromptValidationResult,
    SaveGameStateRequest,
    StateGenerationExamplesResponse,
    StateGenerationRequest,
    StateGenerationResponse,
    TestDataGenerationResult,
    TestScenarioCreate,
    TestScenarioResponse,
    TestScenarioResultCreate,
    TestScenarioResultResponse,
    TestScenarioUpdate,
)
from shared_db.schemas.game_environments import (
    get_environment_variable_schema,
    get_input_schema_for_environment,
    get_output_schema_for_environment,
)
from shared_db.schemas.llm_usage import AgentLLMCostSummary
from shared_db.schemas.user import UserResponse

logger = get_logger(__name__)


agents_router = APIRouter()


# Environment routes (placed before dynamic /agents/{agent_id} to avoid 422)
@agents_router.get("/agents/environments")
async def list_environments(
    _current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> list[GameEnvironmentInfo]:
    return [GameEnvironmentInfo(id=env.value, metadata=meta.model_dump()) for env, meta in _META.items()]


@agents_router.get("/agents/environments/metadata")
async def get_environments_metadata(
    _current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> EnvironmentsMetadataResponse:
    return EnvironmentsMetadataResponse(environments={env.value: meta.model_dump() for env, meta in _META.items()})


@agents_router.get("/agents/environments/{environment_type}/schema")
async def get_environment_schema(
    environment_type: str,
    _current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> GameEnvironmentSchema:
    try:
        env = GameType(environment_type)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Environment '{environment_type}' not found")
    input_schema = get_input_schema_for_environment(env).model_json_schema()
    output_schema = get_output_schema_for_environment(env).model_json_schema()
    variables = get_environment_variable_schema(env)
    return GameEnvironmentSchema(
        environment=env.value,
        input_schema=input_schema,
        output_schema=output_schema,
        variables={k: v.model_dump() for k, v in variables.items()},
    )


@agents_router.get("/agents/environments/{environment_type}/autocomplete")
async def get_environment_autocomplete(
    environment_type: str,
    prefix: Annotated[str, Query(description="Variable prefix to autocomplete")],
    _current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> list[AutocompleteItem]:
    try:
        env = GameType(environment_type)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Environment '{environment_type}' not found")
    variables = get_environment_variable_schema(env)
    return [
        AutocompleteItem(path=path, type=info.type, description=info.description, example=info.example)
        for path, info in variables.items()
        if path.startswith(prefix)
    ]


# Test Scenario Operations (placed before dynamic /agents/{agent_id} to avoid 422)
@agents_router.get("/agents/test-scenarios")
async def get_test_scenarios(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
    environment: Annotated[GameType | None, Query(description="Filter by environment")] = None,
    agent_id: Annotated[AgentId | None, Query(description="Filter by agent")] = None,
    include_system: Annotated[bool, Query(description="Include system-wide scenarios")] = True,
    skip: int = 0,
    limit: int = 100,
) -> list[TestScenarioResponse]:
    """Get test scenarios for the current user."""
    return await agent_service.get_test_scenarios(
        db, user_id=current_user.id, environment=environment, agent_id=agent_id, include_system=include_system, skip=skip, limit=limit
    )


@agents_router.post("/agents/test-scenarios", status_code=status.HTTP_201_CREATED)
async def create_test_scenario(
    scenario_in: TestScenarioCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
) -> TestScenarioResponse:
    """Create a new test scenario."""
    try:
        return await agent_service.create_test_scenario(db, user_id=current_user.id, scenario_in=scenario_in)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@agents_router.post("/agents/test-scenarios/{scenario_id}/results", status_code=status.HTTP_201_CREATED)
async def create_test_result(
    scenario_id: TestScenarioId,
    result_in: TestScenarioResultCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
) -> TestScenarioResultResponse:
    """Create a test result for a scenario."""
    # Ensure scenario_id matches
    if result_in.test_scenario_id != scenario_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Scenario ID mismatch",
        )

    result = await agent_service.create_test_result(db, user_id=current_user.id, result_in=result_in)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test scenario not found",
        )
    return result


@agents_router.get("/agents/test-scenarios/{scenario_id}/results")
async def get_test_results(
    scenario_id: TestScenarioId,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
    skip: int = 0,
    limit: int = 100,
) -> list[TestScenarioResultResponse]:
    """Get test results for a scenario."""
    return await agent_service.get_test_results(db, user_id=current_user.id, scenario_id=scenario_id, skip=skip, limit=limit)


# Synthetic Data Generation Operations (moved before dynamic route)
@agents_router.post("/agents/generate-test-data")
async def generate_test_data(
    instructions: str,
    environment: GameType,
    _current_user: Annotated[UserResponse, Depends(get_current_user)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
) -> TestDataGenerationResult:
    """Generate synthetic test data based on instructions."""
    return agent_service.generate_test_data(instructions, environment)


@agents_router.post("/agents/save-test-scenario")
async def save_test_scenario(
    scenario_in: TestScenarioCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
) -> TestScenarioResponse:
    """Save synthetic data as a test scenario."""
    return await create_test_scenario(scenario_in, db, current_user, agent_service)


@agents_router.get("/agents/test-scenarios/{scenario_id}")
async def get_test_scenario(
    scenario_id: TestScenarioId,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
) -> TestScenarioResponse:
    """Get a single test scenario for the current user."""
    scenario = await agent_service.get_test_scenario(db, user_id=current_user.id, scenario_id=scenario_id)
    if not scenario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test scenario not found")
    return scenario


@agents_router.put("/agents/test-scenarios/{scenario_id}")
async def update_test_scenario(
    scenario_id: TestScenarioId,
    scenario_in: TestScenarioUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
) -> TestScenarioResponse:
    """Update a test scenario for the current user."""
    scenario = await agent_service.update_test_scenario(db, user_id=current_user.id, scenario_id=scenario_id, scenario_in=scenario_in)
    if not scenario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test scenario not found")
    return scenario


@agents_router.delete("/agents/test-scenarios/{scenario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_test_scenario(
    scenario_id: TestScenarioId,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
) -> None:
    """Delete a test scenario."""
    success = await agent_service.delete_test_scenario(db, user_id=current_user.id, scenario_id=scenario_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test scenario not found",
        )


# Agent Version to Agent ID lookup (placed before dynamic /agents/{agent_id} to avoid 422)
@agents_router.get("/agent-versions/{agent_version_id}/agent")
async def get_agent_from_version(
    agent_version_id: AgentVersionId,
    db: Annotated[AsyncSession, Depends(get_db)],
    agent_version_dao: Annotated[AgentVersionDAO, Depends(get_agent_version_dao)],
    _current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> AgentIdLookupResponse:
    """Get the parent agent ID from an agent version ID."""
    version = await agent_version_dao.get(db, agent_version_id)
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent version not found",
        )
    return AgentIdLookupResponse(agent_id=version.agent_id)


# Agent CRUD Operations
@agents_router.get("/agents")
async def get_user_agents(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
    game_environment: Annotated[GameType | None, Query(description="Filter by game environment")] = None,
    skip: int = 0,
    limit: int = 100,
) -> list[AgentResponse]:
    """Get all agents for the current user."""
    return await agent_service.get_user_agents(db, user_id=current_user.id, game_environment=game_environment, skip=skip, limit=limit)


@agents_router.post("/agents", status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_in: AgentCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
) -> AgentResponse:
    """Create a new agent for the current user."""
    return await agent_service.create_agent(db, user_id=current_user.id, agent_in=agent_in)


@agents_router.get("/agents/{agent_id}")
async def get_agent(
    agent_id: AgentId,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
) -> AgentResponse:
    """Get a specific agent for the current user."""
    agent = await agent_service.get_user_agent_by_id(db, user_id=current_user.id, agent_id=agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )
    return agent


@agents_router.put("/agents/{agent_id}")
async def update_agent(
    agent_id: AgentId,
    agent_in: AgentUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
) -> AgentResponse:
    """Update a specific agent for the current user."""
    agent = await agent_service.update_agent(db, user_id=current_user.id, agent_id=agent_id, agent_in=agent_in)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )
    return agent


@agents_router.post("/agents/{agent_id}/clone", status_code=status.HTTP_201_CREATED)
async def clone_agent(
    agent_id: AgentId,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
) -> AgentResponse:
    """Clone an agent (typically a system agent) for the current user.

    Creates a copy of the agent and its active version owned by the current user.
    """
    cloned_agent = await agent_service.clone_agent(db, user_id=current_user.id, agent_id=agent_id)
    if not cloned_agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )
    return cloned_agent


@agents_router.delete("/agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: AgentId,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
) -> None:
    """Delete a specific agent for the current user."""
    success = await agent_service.delete_agent(db, user_id=current_user.id, agent_id=agent_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )


# Agent Version Operations
@agents_router.get("/agents/{agent_id}/versions")
async def get_agent_versions(
    agent_id: AgentId,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
    skip: int = 0,
    limit: int = 100,
) -> list[AgentVersionResponse]:
    """Get all versions for an agent."""
    return await agent_service.get_agent_versions(db, user_id=current_user.id, agent_id=agent_id, skip=skip, limit=limit)


@agents_router.get("/agents/{agent_id}/versions/active")
async def get_active_version(
    agent_id: AgentId,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
) -> AgentVersionResponse:
    """Get the active version for an agent."""
    version = await agent_service.get_active_version(db, user_id=current_user.id, agent_id=agent_id)
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active version found",
        )
    return version


@agents_router.post("/agents/{agent_id}/versions", status_code=status.HTTP_201_CREATED)
async def create_agent_version(
    agent_id: AgentId,
    version_in: AgentVersionCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
) -> AgentVersionResponse:
    """Create a new version for an agent."""
    version = await agent_service.create_version(db, user_id=current_user.id, agent_id=agent_id, version_in=version_in)
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )
    return version


@agents_router.put("/agents/{agent_id}/versions/{version_id}")
async def update_agent_version(
    agent_id: AgentId,
    version_id: AgentVersionId,
    version_in: AgentVersionUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
) -> AgentVersionResponse:
    """Update an agent version (may create new version if version-defining fields change)."""
    version = await agent_service.update_version(db, user_id=current_user.id, agent_id=agent_id, version_id=version_id, version_in=version_in)
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found",
        )
    return version


@agents_router.post("/agents/{agent_id}/versions/{version_id}/activate")
async def activate_version(
    agent_id: AgentId,
    version_id: AgentVersionId,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
) -> AgentVersionResponse:
    """Activate a specific version of an agent."""
    version = await agent_service.activate_version(db, user_id=current_user.id, agent_id=agent_id, version_id=version_id)
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found",
        )
    return version


@agents_router.get("/agents/{agent_id}/versions/limit")
async def get_version_limit_info(
    agent_id: AgentId,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
) -> AgentVersionLimitInfo:
    """Get version limit information for an agent."""
    info = await agent_service.get_version_limit_info(db, user_id=current_user.id, agent_id=agent_id)
    if not info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )
    return info


@agents_router.post("/agents/{agent_id}/versions/compare")
async def compare_versions(
    agent_id: AgentId,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
    version_a_id: Annotated[AgentVersionId, Query(description="First version ID")],
    version_b_id: Annotated[AgentVersionId, Query(description="Second version ID")],
) -> AgentVersionComparisonResponse:
    """Compare two versions of an agent."""
    comparison = await agent_service.compare_versions(db, user_id=current_user.id, agent_id=agent_id, version_a_id=version_a_id, version_b_id=version_b_id)
    if not comparison:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Versions not found",
        )
    return comparison


# Agent Statistics Operations
@agents_router.get("/agents/{agent_id}/statistics")
async def get_agent_statistics(
    agent_id: AgentId,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
) -> AgentStatisticsResponse:
    """Get statistics for an agent."""
    statistics = await agent_service.get_agent_statistics(db, user_id=current_user.id, agent_id=agent_id)
    if not statistics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent statistics not found",
        )
    return statistics


@agents_router.put("/agents/{agent_id}/statistics")
async def update_agent_statistics(
    agent_id: AgentId,
    updates: dict[str, Any],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
) -> AgentStatisticsResponse:
    """Update statistics for an agent."""
    statistics = await agent_service.update_agent_statistics(db, user_id=current_user.id, agent_id=agent_id, updates=updates)
    if not statistics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )
    return statistics


@agents_router.get("/agents/{agent_id}/llm-usage/summary")
async def get_agent_llm_usage_summary(
    agent_id: AgentId,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
) -> AgentLLMCostSummary:
    """Get LLM usage cost summary for an agent (all versions)."""
    # Verify agent ownership
    agent = await agent_service.get_user_agent_by_id(db, user_id=current_user.id, agent_id=agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    # Get cost summary
    llm_usage_dao = LLMUsageDAO()
    summary = await llm_usage_dao.get_agent_cost_summary(db, agent_id=agent_id)
    return summary


class PromptValidationRequest(BaseModel):
    prompt: str
    environment: GameType


@agents_router.post("/agents/validate-prompt")
async def validate_prompt(
    req: PromptValidationRequest,
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
) -> PromptValidationResult:
    """Validate prompt template and check variable references."""
    return agent_service.validate_prompt(req.prompt, req.environment)


# Game State Management Operations
@agents_router.post("/agents/{agent_id}/save-game-state", status_code=status.HTTP_201_CREATED)
async def save_game_state(
    agent_id: AgentId,
    request: SaveGameStateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
) -> TestScenarioResponse:
    """Save a game state as a test scenario for future use."""
    try:
        return await agent_service.save_game_state_as_scenario(
            db,
            user_id=current_user.id,
            agent_id=agent_id,
            name=request.name,
            description=request.description,
            game_state=request.game_state,
            tags=request.tags,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@agents_router.get("/agents/{agent_id}/saved-game-states")
async def get_saved_game_states(
    agent_id: AgentId,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
    tags: Annotated[list[str] | None, Query(description="Filter by tags")] = None,
    skip: int = 0,
    limit: int = 100,
) -> list[TestScenarioResponse]:
    """Get saved game states for a specific agent."""
    return await agent_service.get_saved_game_states(
        db,
        user_id=current_user.id,
        agent_id=agent_id,
        tags=tags,
        skip=skip,
        limit=limit,
    )


# New Test Mechanism Endpoints
@agents_router.post("/agents/{agent_id}/generate-test-json")
async def generate_test_json(
    agent_id: AgentId,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
) -> dict[str, Any]:
    """Generate test JSON for an agent based on its environment.

    Returns a properly structured test input for the agent's game environment.
    """
    try:
        result = await agent_service.generate_test_json(db, current_user.id, agent_id)
        return result.model_dump()
    except ValueError as e:
        if "Agent not found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found",
            )
        if "not yet implemented" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@agents_router.post("/agents/{agent_id}/test")
async def test_agent(
    agent_id: AgentId,
    request: AgentTestRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
) -> AgentTestResponse:
    """Test an agent with the provided game state.

    This endpoint executes a single iteration of agent decision-making.
    If the agent requests a tool, the client should execute it and call this endpoint again.
    """

    # Execute test using AgentService
    result = await agent_service.test_agent_iteration(
        db,
        user_id=current_user.id,
        agent_id=agent_id,
        request=request,
    )

    return result


@agents_router.post("/agents/{agent_id}/generate-state")
async def generate_state(
    agent_id: AgentId,
    request: StateGenerationRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
) -> StateGenerationResponse:
    """Generate a game state from user description using LLM.

    This endpoint uses the specified LLM to generate a realistic game state
    based on the user's description. The generated state is validated against
    the agent's game environment schema.
    """
    try:
        result = await agent_service.generate_state_from_description(
            db,
            user_id=current_user.id,
            agent_id=agent_id,
            request=request,
        )
        return result
    except ValueError as e:
        if "Agent not found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found",
            )
        if "LLM integration not found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="LLM integration not found",
            )
        if "not yet implemented" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


async def _stream_state_chat_ndjson(
    agent_service: AgentService,
    db: AsyncSession,
    user_id: UserId,
    agent_id: AgentId,
    req: StateChatRequest,
):
    async for chunk in agent_service.stream_state_chat(db, user_id, agent_id, req):
        try:
            logger.info(
                "[state_chat_router] chunk",
                extra={
                    "type": chunk.type,
                    "has_final": bool(chunk.final),
                    "is_complete": chunk.is_complete,
                },
            )
        except Exception:
            pass
        yield json.dumps(chunk.model_dump()) + "\n"


@agents_router.get("/agents/{agent_id}/state-chat/examples")
async def get_state_chat_examples(
    agent_id: AgentId,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
) -> StateGenerationExamplesResponse:
    examples = await agent_service.get_state_generation_examples(db, user_id=current_user.id, agent_id=agent_id)
    return StateGenerationExamplesResponse(examples=examples)


# Agent Profile Operations
@agents_router.get("/agents/{agent_id}/profile")
async def get_agent_profile(
    agent_id: AgentId,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
) -> AgentProfileData:
    """Get comprehensive profile data for an agent."""
    from app.services.scoring_service import ScoringService
    from shared_db.crud.agent import AgentDAO, AgentStatisticsDAO
    from shared_db.crud.game import GameDAO
    from shared_db.crud.user import UserDAO

    scoring_service = ScoringService(AgentDAO(), AgentStatisticsDAO(), GameDAO(), UserDAO())

    # Check if user owns the agent
    agent = await agent_service.get_user_agent_by_id(db, user_id=current_user.id, agent_id=agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    profile_data = await scoring_service.get_agent_profile_data(db, agent_id)
    return profile_data


@agents_router.get("/public/agents/{agent_id}")
async def get_public_agent(
    agent_id: AgentId,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> AgentResponse:
    """Get basic public agent information (no ownership check)."""
    from shared_db.crud.agent import AgentDAO

    agent_dao = AgentDAO()
    agent = await agent_dao.get(db, agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )
    return agent


@agents_router.get("/public/agents/{agent_id}/profile")
async def get_public_agent_profile(
    agent_id: AgentId,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> AgentProfileData:
    """Get public profile data for an agent (no personal info)."""
    from app.services.scoring_service import ScoringService
    from shared_db.crud.agent import AgentDAO, AgentStatisticsDAO
    from shared_db.crud.game import GameDAO
    from shared_db.crud.user import UserDAO

    scoring_service = ScoringService(AgentDAO(), AgentStatisticsDAO(), GameDAO(), UserDAO())
    agent_dao = AgentDAO()

    # Get agent without checking ownership
    agent = await agent_dao.get(db, agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    profile_data = await scoring_service.get_agent_profile_data(db, agent_id)

    # Remove personal information for public profile
    public_profile = AgentProfileData(
        agent_id=profile_data.agent_id,
        name=profile_data.name,
        description=profile_data.description,
        game_environment=profile_data.game_environment,
        avatar_url=profile_data.avatar_url,
        avatar_type=profile_data.avatar_type,
        is_system=profile_data.is_system,
        created_at=profile_data.created_at,
        overall_stats=profile_data.overall_stats,
        game_ratings=profile_data.game_ratings,
    )

    return public_profile


@agents_router.get("/agents/{agent_id}/game-rating/{game_type}")
async def get_agent_game_rating(
    agent_id: AgentId,
    game_type: GameType,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
) -> AgentGameRating:
    """Get an agent's rating and statistics for a specific game type."""
    from app.services.scoring_service import ScoringService
    from shared_db.crud.agent import AgentDAO, AgentStatisticsDAO
    from shared_db.crud.game import GameDAO
    from shared_db.crud.user import UserDAO

    scoring_service = ScoringService(AgentDAO(), AgentStatisticsDAO(), GameDAO(), UserDAO())

    # Check if user owns the agent
    agent = await agent_service.get_user_agent_by_id(db, user_id=current_user.id, agent_id=agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    rating_data = await scoring_service.get_agent_game_rating(db, agent_id, game_type)
    return rating_data


@agents_router.get("/public/agents/{agent_id}/game-rating/{game_type}")
async def get_public_agent_game_rating(
    agent_id: AgentId,
    game_type: GameType,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> AgentGameRating:
    """Get public agent rating and statistics for a specific game type."""
    from app.services.scoring_service import ScoringService
    from shared_db.crud.agent import AgentDAO, AgentStatisticsDAO
    from shared_db.crud.game import GameDAO
    from shared_db.crud.user import UserDAO

    scoring_service = ScoringService(AgentDAO(), AgentStatisticsDAO(), GameDAO(), UserDAO())
    agent_dao = AgentDAO()

    # Get agent without checking ownership - verify agent exists
    agent = await agent_dao.get(db, agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    rating_data = await scoring_service.get_agent_game_rating(db, agent_id, game_type)
    return rating_data


@agents_router.get("/leaderboard")
async def get_leaderboard(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[UserResponse, Depends(get_current_user)],
    game_type: Annotated[GameType | None, Query(description="Filter by game type")] = None,
    limit: int = Query(default=100, le=1000),
) -> list[AgentProfileData]:
    """Get leaderboard of agents sorted by rating for a specific game type.

    Returns agents with their statistics and ratings, sorted by rating (highest first).
    Both user agents and system agents are included.
    """

    from shared_db.crud.user import UserDAO

    agent_dao = AgentDAO()
    scoring_service = ScoringService(agent_dao, AgentStatisticsDAO(), GameDAO(), UserDAO())

    # Get all active agents, optionally filtered by game environment
    # Exclude agents that cannot play in real matches (playground-only agents)
    query = select(Agent).where(~Agent.is_archived, Agent.can_play_in_real_matches == True)

    if game_type:
        query = query.where(Agent.game_environment == game_type)

    # Join with statistics to filter agents with games played and sort by rating
    query = query.join(AgentStatistics, Agent.id == AgentStatistics.agent_id, isouter=True)

    result = await db.execute(query.limit(limit))
    agents = result.scalars().all()

    # Get profile data for each agent and extract their rating for the specified game type
    leaderboard_entries: list[tuple[AgentProfileData, float, int]] = []

    for agent in agents:
        try:
            profile_data = await scoring_service.get_agent_profile_data(db, agent.id)

            # Determine which rating to use for sorting
            if game_type:
                # Use specific game type rating
                game_rating = profile_data.game_ratings.get(game_type.value)
                if game_rating:
                    # Include all agents, even with 0 games (they'll have default rating)
                    leaderboard_entries.append((profile_data, game_rating.rating, game_rating.games_played))
            else:
                # Use the highest rating across all games
                max_rating = 0.0
                total_games = 0
                for game_rating in profile_data.game_ratings.values():
                    max_rating = max(max_rating, game_rating.rating)
                    total_games += game_rating.games_played

                # Include all agents, even with 0 games
                leaderboard_entries.append((profile_data, max_rating, total_games))
        except Exception as e:
            logger.warning(f"Failed to get profile for agent {agent.id}: {e}")
            continue

    # Sort by games played first (desc), then rating (desc)
    # This puts agents with games at the top, sorted by rating
    # Agents with no games appear at the bottom, sorted by default rating
    leaderboard_entries.sort(key=lambda x: (x[2], x[1]), reverse=True)

    # Return just the profile data
    return [entry[0] for entry in leaderboard_entries]


@agents_router.post("/agents/update-game-ratings")
async def update_game_ratings(
    request: GameRatingUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
) -> GameRatingUpdateResponse:
    """Update agent ratings after a game completes."""

    game_dao = GameDAO()
    scoring_service = ScoringService(AgentDAO(), AgentStatisticsDAO(), game_dao)

    # Get the game
    game = await game_dao.get(db, request.game_id)
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found",
        )

    # Extract game result from state
    registry = GameEnvRegistry.instance()
    env_class = registry.get(game.game_type)
    state = env_class.types().state_type().model_validate(game.state)
    game_result = env_class.extract_game_result(state)

    # Verify all agents in the game belong to the current user
    for agent_id in request.agent_mapping.values():
        agent = await agent_service.get_user_agent_by_id(db, user_id=current_user.id, agent_id=agent_id)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update ratings for your own agents",
            )

    # Update ratings
    response = await scoring_service.update_agent_ratings_after_game(db, request, game_result)

    logger.info(
        f"Updated ratings for game {request.game_id}",
        extra={"game_type": request.game_type.value, "num_agents": len(request.agent_mapping), "user_id": str(current_user.id)},
    )

    return response


@agents_router.post("/agents/{agent_id}/state-chat/stream")
async def stream_state_chat(
    agent_id: AgentId,
    request: StateChatRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
) -> StreamingResponse:
    return StreamingResponse(
        _stream_state_chat_ndjson(agent_service, db, current_user.id, agent_id, request),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

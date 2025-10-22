"""Agent test service for testing and validation operations."""

import contextlib
import json
import re
import time
from collections.abc import AsyncGenerator
from typing import Any, cast

from game_api import GameType
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.state_chat import StateChatFinalPayload, StateChatRequest, StateChatStreamChunk
from app.services.game_env_registry import GameEnvRegistry
from app.services.game_schema_helper import build_player_view_schema
from app.services.llm_integration_service import LLMIntegrationService
from common.core.litellm_schemas import ChatMessage, LiteLLMConfig, MessageRole
from common.core.litellm_service import LiteLLMService
from common.core.logging_service import get_logger
from common.enums import LLMProvider
from common.ids import AgentId, PlayerId, TestScenarioId, UserId
from common.utils.tsid import TSID
from shared_db.crud.agent import AgentDAO, AgentVersionDAO, TestScenarioDAO
from shared_db.schemas.agent import (
    AgentTestJsonResult,
    StateGenerationRequest,
    StateGenerationResponse,
    TestDataGenerationResult,
    TestScenarioCreate,
    TestScenarioResponse,
    TestScenarioResultCreate,
    TestScenarioResultResponse,
    TestScenarioUpdate,
)

logger = get_logger(__name__)


class AgentTestService:
    """Service layer for agent testing operations.
    Handles test scenarios, state generation, and test execution.
    """

    def __init__(
        self,
        agent_dao: AgentDAO,
        test_scenario_dao: TestScenarioDAO,
        llm_integration_service: LLMIntegrationService,
        llm_service: LiteLLMService,
    ) -> None:
        """Initialize AgentTestService with DAO dependencies.

        Args:
            agent_dao: AgentDAO instance for agent operations
            test_scenario_dao: TestScenarioDAO instance for test scenario operations
            llm_integration_service: LLMIntegrationService instance for LLM operations
            llm_service: LiteLLMService instance for LLM API calls
        """
        self.agent_dao = agent_dao
        self.test_scenario_dao = test_scenario_dao
        self.llm_integration_service = llm_integration_service
        self.llm_service = llm_service

    # Test Scenario Operations
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
        """Get test scenarios for a user.

        Args:
            db: Database session
            user_id: User ID
            environment: Optional environment filter
            agent_id: Optional agent ID filter
            include_system: Whether to include system-wide scenarios (default: True)
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of TestScenarioResponse objects
        """
        logger.info(f"Getting test scenarios for user {user_id}, include_system={include_system}")

        if agent_id:
            # Verify agent ownership and expand to all scenarios for this environment
            agent = await self.agent_dao.get_by_user_and_id(db, user_id=user_id, agent_id=agent_id)
            if not agent:
                return []
            scenarios = await self.test_scenario_dao.get_by_user(db, user_id=user_id, environment=agent.game_environment, skip=skip, limit=limit)
        else:
            scenarios = await self.test_scenario_dao.get_by_user(db, user_id=user_id, environment=environment, skip=skip, limit=limit)

        # Filter out system scenarios if requested
        if not include_system:
            scenarios = [s for s in scenarios if not s.is_system]

        return scenarios

    async def create_test_scenario(
        self,
        db: AsyncSession,
        *,
        user_id: UserId,
        scenario_in: TestScenarioCreate,
    ) -> TestScenarioResponse:
        """Create a new test scenario.

        Args:
            db: Database session
            user_id: User ID
            scenario_in: Test scenario creation data

        Returns:
            Created TestScenarioResponse
        """
        logger.info(f"Creating test scenario for user {user_id}: {scenario_in.name}")

        return await self.test_scenario_dao.create(db, obj_in=scenario_in, user_id=user_id)

    async def create_test_result(
        self,
        db: AsyncSession,
        *,
        user_id: UserId,
        result_in: TestScenarioResultCreate,
    ) -> TestScenarioResultResponse | None:
        """Create a test scenario result.

        Args:
            db: Database session
            user_id: User ID
            result_in: Test result creation data

        Returns:
            Created TestScenarioResultResponse if successful, None otherwise
        """
        logger.info(f"Creating test result for scenario {result_in.test_scenario_id}")

        # Verify test scenario ownership
        scenarios = await self.test_scenario_dao.get_by_user(db, user_id=user_id, skip=0, limit=1000)
        scenario = next((s for s in scenarios if s.id == result_in.test_scenario_id), None)
        if not scenario:
            return None

        return await self.test_scenario_dao.create_result(db, obj_in=result_in)

    async def get_test_results(
        self,
        db: AsyncSession,
        *,
        user_id: UserId,
        scenario_id: TestScenarioId,
        skip: int = 0,
        limit: int = 100,
    ) -> list[TestScenarioResultResponse]:
        """Get test results for a scenario.

        Args:
            db: Database session
            user_id: User ID
            scenario_id: Test scenario ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of TestScenarioResultResponse objects
        """
        logger.info(f"Getting test results for scenario {scenario_id}")

        # Verify test scenario ownership
        scenarios = await self.test_scenario_dao.get_by_user(db, user_id=user_id, skip=0, limit=1000)
        scenario = next((s for s in scenarios if s.id == scenario_id), None)
        if not scenario:
            return []

        return await self.test_scenario_dao.get_results(db, scenario_id=scenario_id, skip=skip, limit=limit)

    async def delete_test_scenario(self, db: AsyncSession, user_id: UserId, scenario_id: TestScenarioId) -> bool:
        """Delete a test scenario.

        Args:
            db: Database session
            user_id: User ID for ownership verification
            scenario_id: Test scenario ID to delete

        Returns:
            True if deleted successfully, False if not found or not owned by user
        """
        logger.info(f"Deleting test scenario {scenario_id} for user {user_id}")

        # Verify ownership by getting the scenario first
        scenario = await self.test_scenario_dao.get(db, id=scenario_id)
        if not scenario:
            return False

        # Cannot delete system scenarios
        if scenario.is_system:
            logger.warning(f"Attempted to delete system scenario {scenario_id}")
            return False

        # Must be owned by the user
        if scenario.user_id != user_id:
            return False

        # Use DAO to delete
        return await self.test_scenario_dao.delete(db, id=scenario_id)

    async def get_test_scenario(self, db: AsyncSession, *, user_id: UserId, scenario_id: TestScenarioId) -> TestScenarioResponse | None:
        """Get a single test scenario if owned by the user or if it's a system scenario."""
        scenario = await self.test_scenario_dao.get(db, id=scenario_id)
        if not scenario:
            return None
        # Allow access if it's the user's scenario OR if it's a system scenario
        if scenario.user_id != user_id and not scenario.is_system:
            return None
        return scenario

    async def update_test_scenario(
        self,
        db: AsyncSession,
        *,
        user_id: UserId,
        scenario_id: TestScenarioId,
        scenario_in: TestScenarioUpdate,
    ) -> TestScenarioResponse | None:
        """Update a test scenario if owned by the user. System scenarios cannot be updated."""
        # Verify ownership
        existing = await self.test_scenario_dao.get(db, id=scenario_id)
        if not existing:
            return None

        # Cannot update system scenarios
        if existing.is_system:
            logger.warning(f"Attempted to update system scenario {scenario_id}")
            return None

        # Must be owned by the user
        if existing.user_id != user_id:
            return None

        return await self.test_scenario_dao.update_by_id(db, id=scenario_id, obj_in=scenario_in)

    # Game State Management Operations
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
        """Save a game state as a test scenario for future use.

        Args:
            db: Database session
            user_id: User ID
            agent_id: Agent ID to associate with the saved state
            name: Name for the saved game state
            description: Optional description
            game_state: The game state JSON to save
            tags: Optional tags for categorization

        Returns:
            Created TestScenarioResponse
        """
        logger.info(f"Saving game state as scenario for user {user_id}, agent {agent_id}: {name}")

        # Verify agent ownership
        agent = await self.agent_dao.get_by_user_and_id(db, user_id=user_id, agent_id=agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found or not owned by user")

        # Create test scenario with game state
        scenario_in = TestScenarioCreate(
            name=name,
            description=description,
            environment=agent.game_environment,
            game_state=game_state,
            tags=tags or [],
        )

        return await self.test_scenario_dao.create(db, obj_in=scenario_in, user_id=user_id)

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
        """Get saved game states (test scenarios) for a user.

        Args:
            db: Database session
            user_id: User ID
            agent_id: Optional agent ID filter
            environment: Optional environment filter
            tags: Optional tags filter
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of TestScenarioResponse objects
        """
        logger.info(f"Getting saved game states for user {user_id}")

        if agent_id:
            # Verify agent ownership and expand to all scenarios for this environment
            agent = await self.agent_dao.get_by_user_and_id(db, user_id=user_id, agent_id=agent_id)
            if not agent:
                return []
            return await self.test_scenario_dao.get_by_user(db, user_id=user_id, environment=agent.game_environment, skip=skip, limit=limit)

        # Get scenarios filtered by environment
        scenarios = await self.test_scenario_dao.get_by_user(db, user_id=user_id, environment=environment, skip=skip, limit=limit)

        # Apply tags filter if provided
        if tags:
            filtered_scenarios: list[TestScenarioResponse] = []
            for scenario in scenarios:
                scenario_tags = scenario.tags or []
                if any(tag in scenario_tags for tag in tags):
                    filtered_scenarios.append(scenario)
            return filtered_scenarios

        return scenarios

    # Test Data Generation Operations
    def generate_test_data(self, instructions: str, environment: GameType) -> TestDataGenerationResult:
        """Generate synthetic test data based on instructions.

        Args:
            instructions: Instructions for test data generation
            environment: Game environment to generate data for

        Returns:
            TestDataGenerationResult with generated game state
        """
        logger.info(f"Generating test data for environment {environment} with instructions: {instructions}")

        # This would use an LLM to generate test data
        # For now, return a placeholder with realistic poker data
        return TestDataGenerationResult(
            game_state={
                "players": [
                    {"chips": 1000, "position": "button", "cards": ["As", "Kd"]},
                    {"chips": 800, "position": "small_blind", "cards": ["?", "?"]},
                    {"chips": 1200, "position": "big_blind", "cards": ["?", "?"]},
                ],
                "pot": 150,
                "community_cards": ["Ah", "Kh", "Qc"],
                "current_bet": 50,
                "min_raise": 100,
                "stage": "flop",
            },
            description="Generated test scenario based on instructions",
        )

    async def generate_test_json(self, db: AsyncSession, user_id: UserId, agent_id: AgentId) -> AgentTestJsonResult[Any]:
        """Generate test JSON for an agent based on its environment.

        Args:
            db: Database session
            user_id: User ID for ownership verification
            agent_id: Agent ID to generate test data for

        Returns:
            AgentTestJsonResult with generated test input

        Raises:
            ValueError: If agent not found or environment not supported
        """
        logger.info(f"Generating test JSON for agent {agent_id}")

        # Validate agent ownership
        agent = await self.agent_dao.get_by_user_and_id(db, user_id=user_id, agent_id=agent_id)
        if not agent:
            raise ValueError("Agent not found")

        # Generate environment-specific test JSON
        # For now, we only support Texas Hold'em
        if agent.game_environment.value != "texas_holdem":
            raise ValueError(f"Test generation not yet implemented for {agent.game_environment.value}")

        # Import here to avoid circular imports
        from texas_holdem.texas_holdem_api import (
            BettingRound,
            Card,
            CardRank,
            CardSuit,
            PlayerStatus,
            TexasHoldemAction,
            TexasHoldemOtherPlayerView,
            TexasHoldemPlayer,
            TexasHoldemPossibleMove,
            TexasHoldemPossibleMoves,
            TexasHoldemStateView,
        )

        from common.utils.tsid import TSID
        from shared_db.schemas.game_environments import TexasHoldemAgentInput

        # Create a sample Texas Hold'em test scenario with realistic data
        # Player has A♥ K♠ (ace high straight draw)
        # Flop shows Q♦ J♣ 10♥ - player needs any 9 or A for straight
        test_state = TexasHoldemStateView(
            betting_round=BettingRound.FLOP,
            community_cards=[
                Card(rank=CardRank.QUEEN, suit=CardSuit.DIAMONDS),
                Card(rank=CardRank.JACK, suit=CardSuit.CLUBS),
                Card(rank=CardRank.TEN, suit=CardSuit.HEARTS),
            ],
            # Current player (me) - includes hole cards for autocomplete
            me=TexasHoldemPlayer(
                player_id=PlayerId(TSID.create()),
                chips=950,
                status=PlayerStatus.ACTIVE,
                current_bet=25,
                total_bet=75,
                position=0,
                hole_cards=[
                    Card(rank=CardRank.ACE, suit=CardSuit.HEARTS),
                    Card(rank=CardRank.KING, suit=CardSuit.SPADES),
                ],
            ),
            # Players who already played in this round
            already_played_players=[
                TexasHoldemOtherPlayerView(
                    player_id=PlayerId(TSID.create()),
                    chips=800,
                    status=PlayerStatus.FOLDED,
                    current_bet=0,
                    total_bet=25,
                    position=2,
                ),
            ],
            # Players still to play in this round
            should_play_players=[
                TexasHoldemOtherPlayerView(
                    player_id=PlayerId(TSID.create()),
                    chips=1000,
                    status=PlayerStatus.ACTIVE,
                    current_bet=50,
                    total_bet=100,
                    position=1,
                ),
            ],
            pot=150,
            side_pots=[],
            current_bet=50,
            dealer_position=0,
            small_blind_position=1,
            big_blind_position=2,
            last_raise_amount=50,
            last_raise_position=2,
            winners=None,
            winning_hands=None,
        )

        test_input = TexasHoldemAgentInput(
            state=test_state,
            possible_moves=TexasHoldemPossibleMoves(
                possible_moves=[
                    TexasHoldemPossibleMove(action=TexasHoldemAction.FOLD),
                    TexasHoldemPossibleMove(action=TexasHoldemAction.CALL, amount=25),
                    TexasHoldemPossibleMove(
                        action=TexasHoldemAction.RAISE,
                        min_raise_amount=100,
                        max_raise_amount=950,
                    ),
                ],
            ),
            player_id=AgentId(TSID.create()),
            iteration_history=[],
        )

        return AgentTestJsonResult(
            test_input=test_input,
            description="Texas Hold'em test scenario: Player has A♥ K♠, Flop (Q♦ J♣ 10♥), straight draw, pot 150, facing 25 to call",
            environment=agent.game_environment,
        )

    async def generate_state_from_description(
        self,
        db: AsyncSession,
        user_id: UserId,
        agent_id: AgentId,
        request: StateGenerationRequest,
    ) -> StateGenerationResponse:
        """Generate a game state from user description using LLM.

        Args:
            db: Database session
            user_id: User ID for ownership verification
            agent_id: Agent ID to get environment context
            request: State generation request with description and LLM ID

        Returns:
            StateGenerationResponse with generated and validated state

        Raises:
            ValueError: If agent not found or environment not supported
            Exception: If LLM generation or validation fails
        """
        start_time = time.time()
        logger.info(f"Generating state from description for agent {agent_id}")

        # Validate agent ownership
        agent = await self.agent_dao.get_by_user_and_id(db, user_id=user_id, agent_id=agent_id)
        if not agent:
            raise ValueError("Agent not found")

        # Resolve active agent version to determine slow model/provider
        version = await AgentVersionDAO().get_active_version(db, agent_id=agent_id)
        if not version:
            raise ValueError("Active agent version not found")

        # Get user's integration for the slow provider
        slow_integration = await self.llm_integration_service.get_user_integration_by_provider_with_key(db, user_id, version.slow_llm_provider)
        if not slow_integration:
            raise ValueError("Slow LLM integration not found for this agent")

        # Get game environment class for state generation
        from app.services.game_env_registry import GameEnvRegistry

        game_env_registry = GameEnvRegistry.instance()
        game_env_class = game_env_registry.get(agent.game_environment)

        try:
            # Build system prompt with authoritative JSON schema for player-view
            schema_json = build_player_view_schema(game_env_class)
            system_prompt = game_env_class.get_state_generation_system_prompt() + "\n\nJSON Schema (authoritative, use exact keys and types):\n" + schema_json
            user_prompt = game_env_class.create_state_generation_user_prompt(request.description)

            # Call LLM
            messages = [
                ChatMessage(role=MessageRole.SYSTEM, content=system_prompt),
                ChatMessage(role=MessageRole.USER, content=user_prompt),
            ]

            config = LiteLLMConfig(
                temperature=0.7,  # Some creativity for varied scenarios
                max_tokens=2000,
            )

            model_used = version.slow_llm_model or slow_integration.selected_model
            llm_response = await self.llm_service.chat_completion(
                provider=LLMProvider(slow_integration.provider),
                model=cast(Any, model_used),
                messages=messages,
                api_key=slow_integration.api_key,
                output_type=str,
                config=config,
            )

            # Parse and validate the response
            try:
                response_content = llm_response.content
                if not response_content:
                    raise ValueError("Empty response from LLM")

                # Extract JSON from response (handle potential markdown formatting)
                json_content = self._extract_json_from_response(response_content)
                state_data = json.loads(json_content)

                # Validate using game environment (schema only), then domain checks
                validated_state_obj = game_env_class.validate_generated_state(state_data)
                validated_state_obj = game_env_class.validate_test_json(validated_state_obj)
                # Convert back to dict for API response (frontend expects JSON)
                validated_state = validated_state_obj.model_dump()

                generation_time_ms = int((time.time() - start_time) * 1000)

                return StateGenerationResponse(
                    state=validated_state,
                    description=f"Generated Texas Hold'em state: {request.description}",
                    environment=agent.game_environment,
                    generation_time_ms=generation_time_ms,
                    model_used=llm_response.model,
                    input_tokens=llm_response.usage.prompt_tokens if llm_response.usage else None,
                    output_tokens=llm_response.usage.completion_tokens if llm_response.usage else None,
                    total_tokens=llm_response.usage.total_tokens if llm_response.usage else None,
                    cost_usd=llm_response.cost_usd,
                )

            except (json.JSONDecodeError, ValueError) as e:
                logger.exception("Failed to parse LLM response")
                raise ValueError(f"Invalid response from LLM: {e}")

        except Exception:
            logger.exception("Error during state generation")
            raise

    def _extract_json_from_response(self, response: str) -> str:
        """Extract the final JSON object from a mixed LLM response.

        Strategy:
        1) Look for fenced code blocks (```json ... ```). Try the LAST block first.
           Return the first block that parses as JSON.
        2) Fallback: scan for balanced JSON objects and try to parse them, starting
           from the end. Prefer objects that look like our wrapper (has 'state' or
           both 'description' and 'message'). If none match, return the largest
           parsed JSON object.
        """

        s = (response or "").strip()
        if not s:
            raise ValueError("Empty response")

        # Preprocess: if response begins with a single unclosed code fence, drop the fence line
        if s.startswith("```") and s.count("```") == 1:
            s = "\n".join(s.splitlines()[1:]).strip()

        # 1) Try code-fenced blocks from the end
        fence = re.compile(r"```(?:json|javascript|js)?\s*([\s\S]*?)```", re.IGNORECASE)
        blocks = [m.group(1).strip() for m in fence.finditer(s)]
        for content in reversed(blocks):
            try:
                json.loads(content)
                return content
            except Exception:
                logger.debug("Ignoring non-JSON fenced block during extraction")
                continue

        # 2) Balanced JSON scan: iterate over '{' positions from the end
        def balanced_from(index: int) -> str | None:
            depth = 0
            in_str = False
            esc = False
            for j in range(index, len(s)):
                ch = s[j]
                if in_str:
                    if esc:
                        esc = False
                    elif ch == "\\":
                        esc = True
                    elif ch == '"':
                        in_str = False
                elif ch == '"':
                    in_str = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        return s[index : j + 1]
            return None

        candidates: list[tuple[int, str]] = []  # (length, json_str)
        for i in range(len(s) - 1, -1, -1):
            if s[i] == "{":
                frag = balanced_from(i)
                if frag:
                    try:
                        parsed = json.loads(frag)
                        if isinstance(parsed, dict):
                            candidates.append((len(frag), frag))
                    except Exception:
                        logger.debug("Skipping invalid JSON candidate during balanced scan")

        if not candidates:
            # No balanced JSON object was found; likely incomplete/truncated output
            raise ValueError("Incomplete or malformed JSON in model output (no balanced object found)")

        # Prefer wrappers with 'state' or description/message present
        def score(js: str) -> tuple[int, int]:
            try:
                obj = json.loads(js)
                if isinstance(obj, dict):
                    obj_dict = cast(dict[str, Any], obj)
                    has_state = 1 if "state" in obj_dict and isinstance(obj_dict.get("state"), dict) else 0
                    has_desc_msg = 1 if (isinstance(obj_dict.get("description"), str) or isinstance(obj_dict.get("message"), str)) else 0
                    return (has_state + has_desc_msg, len(js))
            except Exception:
                logger.debug("Failed to score candidate JSON during extraction")
            return (0, len(js))

        # Pick best scored candidate (state/desc/message), tie-breaker by length
        candidates.sort(key=lambda t: (score(t[1])[0], score(t[1])[1]))
        best = candidates[-1][1]
        return best

    def extract_json_from_response(self, response: str) -> str:
        """Alias for _extract_json_from_response for external callers."""
        return self._extract_json_from_response(response)

    def _normalize_player_ids(self, state: Any) -> Any:
        """Normalize playerId-like fields to canonical TSID strings consistently.

        - Maps any non-TSID identifiers (e.g., ULID-like 26-char strings or labels like
          'player_sb', 'player_bb') to freshly generated TSIDs.
        - Ensures the same original identifier maps to the same TSID across the whole state.
        - Only affects fields that are expected to be PlayerId values: keys named 'playerId'
          (camelCase alias) or 'player_id', and list under 'winners'.
        """
        id_map: dict[str, str] = {}

        def is_valid_tsid(value: str) -> bool:
            try:
                _ = TSID.from_string_by_length(value)
                return True
            except Exception:
                return False

        def map_id(value: Any) -> Any:
            if isinstance(value, str):
                # Keep valid TSIDs unchanged; otherwise map ANY non-TSID string
                if is_valid_tsid(value):
                    return value
                if value not in id_map:
                    id_map[value] = TSID.create().to_string("s")
                return id_map[value]
            return value

        def walk(node: Any) -> Any:
            if isinstance(node, dict):
                new_obj: dict[str, Any] = {}
                for k, v in node.items():
                    if k in ("playerId", "player_id"):
                        new_obj[k] = map_id(v)
                    elif k == "winners" and isinstance(v, list):
                        new_obj[k] = [map_id(i) for i in v]
                    else:
                        new_obj[k] = walk(v)
                return new_obj
            if isinstance(node, list):
                return [walk(i) for i in node]
            return node

        return walk(state)

    async def stream_state_chat(
        self,
        db: AsyncSession,
        user_id: UserId,
        agent_id: AgentId,
        req: StateChatRequest,
    ) -> AsyncGenerator[StateChatStreamChunk]:
        """Stream a chat-first state generation/editing turn (unified service).

        - Sends full conversation history each turn
        - If req.current_state is provided -> edit mode; else -> generate mode
        - Streams assistant tokens as content chunks, then emits a final payload with
          validated state JSON and an LLM-rewritten description.
        """
        # Verify agent exists and belongs to user
        agent = await self.agent_dao.get_by_user_and_id(db, user_id=user_id, agent_id=agent_id)
        if not agent:
            yield StateChatStreamChunk(type="error", error="Agent not found", is_complete=True)
            return

        # Resolve game environment class
        game_env_class = GameEnvRegistry.instance().get(agent.game_environment)

        # Use the user's selected LLM integration from the request
        try:
            integration = await self.llm_integration_service.get_integration_for_use(db, req.llm_integration_id)
        except Exception:
            logger.exception("[state_chat] failed to load user-selected integration")
            yield StateChatStreamChunk(type="error", error="LLM integration not found or access denied", is_complete=True)
            return

        # Compose messages for LLM: env guidance + authoritative JSON schema + wrapper instruction
        schema_json = build_player_view_schema(game_env_class)
        system_prompt = (
            game_env_class.get_state_generation_system_prompt()
            + "\n\nJSON Schema (authoritative, use exact keys and types):\n"
            + schema_json
            + "\n\nOUTPUT CONTRACT — REQUIRED (this supersedes any earlier format hints)\n"
            + "Return EXACTLY ONE JSON object with the following top-level keys:\n"
            + '- "message": string — a brief, user-facing assistant message\n'
            + '- "description": string — a human-readable summary aligned with the final state\n'
            + '- "state": object — MUST conform EXACTLY to the JSON Schema above\n\n'
            + 'STRICT VALIDATION FOR "state"\n'
            + "- The JSON Schema above is authoritative. You must:\n"
            + "  • Use camelCase property names exactly as defined by the schema's aliases\n"
            + "  • Include all required fields; do not omit required data\n"
            + "  • Use correct types and enum values for every field\n"
            + "  • Match the exact array/object shapes and nesting described by the schema\n"
            + "- If any value is unknown, pick a valid value permitted by the schema. Do NOT remove required fields.\n"
            + "- PlayerId fields: use canonical TSID strings (13-character IDs) and ensure they match the same playerId values you output for players. Do not use labels like 'player_sb' or 'player_bb'; always reference actual playerId values.\n\n"
            + "EMISSION RULES\n"
            + "- Output only the single JSON object. No extra text before or after.\n"
            + "- Do NOT wrap the output in markdown fences (no ```).\n"
            + "- Do NOT stream partial JSON; emit only the final complete object.\n"
        )

        messages: list[ChatMessage] = [ChatMessage(role=MessageRole.SYSTEM, content=system_prompt)]

        # Add full conversation history
        for m in req.conversation_history:
            role = MessageRole.USER if m.writer == "human" else MessageRole.ASSISTANT
            messages.append(ChatMessage(role=role, content=m.content))

        # Add current user message and optional state context
        user_msg_parts: list[str] = [f"User request: {req.message}"]
        if req.current_state is not None:
            try:
                user_msg_parts.append("\nCurrent state JSON to edit:\n```json\n" + json.dumps(req.current_state) + "\n```")
                user_msg_parts.append("\nEdit the state to reflect this request and keep it valid.")
            except Exception:
                user_msg_parts.append("\nCurrent state provided; edit to reflect the request and keep it valid.")
        else:
            user_msg_parts.append("\nGenerate a new valid player-view state (not full engine state).")

        messages.append(ChatMessage(role=MessageRole.USER, content="".join(user_msg_parts)))

        provider = LLMProvider(integration.provider)
        # Use model_id from request if provided, otherwise fall back to integration's default
        model_used = req.model_id if req.model_id else integration.selected_model
        logger.info(f"[state_chat] Using model: {model_used} (from request: {req.model_id}, integration default: {integration.selected_model})")
        config = LiteLLMConfig(stream=True, max_tokens=4000, temperature=0.7)

        # Emit start marker
        yield StateChatStreamChunk(type="content", content=None)

        accumulated: str = ""
        total_chars: int = 0
        try:
            async for token in self.llm_service.stream_chat_completion(
                provider=provider,
                model=cast(Any, model_used),
                messages=messages,
                api_key=integration.api_key,
                config=config,
            ):
                accumulated += token
                total_chars += len(token)
                yield StateChatStreamChunk(type="content", content=token)
        except Exception as e:
            logger.exception("[state_chat] error during token streaming")
            yield StateChatStreamChunk(type="error", error=str(e), is_complete=True)
            return

        # After streaming completes, extract the final JSON wrapper and validate
        try:
            if total_chars == 0 or accumulated.strip() == "":
                yield StateChatStreamChunk(type="error", error="Empty response from LLM provider", is_complete=True)
                return

            json_str = self.extract_json_from_response(accumulated)
            payload = json.loads(json_str)

            # Allow either wrapped payload or raw state for robustness
            if isinstance(payload, dict):
                payload_dict = cast(dict[str, Any], payload)
                raw_state = payload_dict.get("state", payload_dict)
                desc_val = str(cast(Any, payload_dict.get("description")) or "")
                msg_val = str(cast(Any, payload_dict.get("message")) or "").strip()
            else:
                raw_state = payload
                desc_val = ""
                msg_val = ""

            # Normalize playerId strings and validate via env
            raw_state = self._normalize_player_ids(raw_state)
            validated_obj = game_env_class.validate_generated_state(raw_state)
            validated_obj = game_env_class.validate_test_json(validated_obj)
            validated_state = validated_obj.model_dump()

            final_payload = StateChatFinalPayload(
                state=validated_state,
                description=desc_val,
                message=msg_val,
            )
            yield StateChatStreamChunk(type="done", final=final_payload, is_complete=True)
        except Exception as e:
            logger.exception("[state_chat] error building final payload")
            with contextlib.suppress(Exception):
                logger.exception(f"[state_chat] accumulated LLM response (raw):\n{accumulated}")
            yield StateChatStreamChunk(type="error", error=str(e), is_complete=True)
            return

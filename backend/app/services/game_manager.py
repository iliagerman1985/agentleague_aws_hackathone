"""Game manager for orchestrating turn-based games with lease-based processing."""

import asyncio
import contextlib
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta
from typing import Any, cast

from api.agentcore_api import AgentExecutionContext
from game_api import (
    BaseGameConfig,
    BaseGameEvent,
    BaseGameState,
    BaseGameStateView,
    BasePlayerMoveData,
    BasePlayerPossibleMoves,
    EventCollector,
    GameAnalysisHandler,
    GameType,
    GenericGameEnv,
    GenericPlayerMove,
    PlayerMove,
)
from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.scoring import GameRatingUpdateRequest
from app.services.agent_execution_service import AgentExecutionService
from app.services.agent_runner import AgentRunner
from app.services.game_env_registry import GameEnvRegistry
from app.services.llm_integration_service import LLMIntegrationService
from app.services.scoring_service import ScoringService
from app.services.stockfish_agent_executor import execute_brain_bot_move
from common.core.app_error import Errors, should_retry_exception
from common.ids import AgentId, AgentVersionId, GameId, PlayerId, RequestId, UserId
from common.types import AgentReasoning
from common.utils.tsid import TSID
from common.utils.utils import get_logger, get_now
from shared_db.crud.agent import AgentStatisticsDAO, AgentVersionDAO
from shared_db.crud.game import GameDAO
from shared_db.crud.tool import ToolDAO
from shared_db.models.game import Game, GamePlayer, MatchmakingStatus
from shared_db.models.tool import ToolValidationStatus
from shared_db.schemas.agent import AgentVersionResponse

logger = get_logger()

GAME_PROCESSING_TIMEOUT = timedelta(minutes=4)
HEARTBEAT_TIMEOUT = timedelta(minutes=3)


class GameManager:
    """This is the main orchestrator that handles game state transitions,
    move validation, and game flow. It delegates env-specific logic
    to the appropriate GameEnv implementation.
    """

    _registry: GameEnvRegistry
    _agent_execution_service: AgentExecutionService
    _game_dao: GameDAO
    _agent_version_dao: AgentVersionDAO
    _agent_statistics_dao: AgentStatisticsDAO
    _tool_dao: ToolDAO
    _llm_integration_service: LLMIntegrationService
    _agent_runner: AgentRunner
    _scoring_service: ScoringService
    _sqs_game_analysis_handler: GameAnalysisHandler

    def __init__(
        self,
        registry: GameEnvRegistry,
        agent_execution_service: AgentExecutionService,
        game_dao: GameDAO,
        agent_version_dao: AgentVersionDAO,
        agent_statistics_dao: AgentStatisticsDAO,
        tool_dao: ToolDAO,
        llm_integration_service: LLMIntegrationService,
        agent_runner: AgentRunner,
        scoring_service: ScoringService,
        sqs_game_analysis_handler: GameAnalysisHandler,
    ) -> None:
        self._registry = registry
        self._agent_execution_service = agent_execution_service
        self._game_dao = game_dao
        self._agent_version_dao = agent_version_dao
        self._agent_statistics_dao = agent_statistics_dao
        self._tool_dao = tool_dao
        self._llm_integration_service = llm_integration_service
        self._agent_runner = agent_runner
        self._scoring_service = scoring_service
        self._sqs_game_analysis_handler = sqs_game_analysis_handler

    async def update_ratings_for_finished_game(
        self,
        db: AsyncSession,
        game: Game,
        state: BaseGameState,
        env_type: type[GenericGameEnv],
    ) -> None:
        """Update agent ratings for a finished game.

        Only updates ratings for competitive (non-playground) games.
        This is a public method that can be called by other services.

        Args:
            db: Database session
            game: Game object
            state: Final game state
            env_type: Game environment type
        """
        # Skip rating updates for playground games
        if game.is_playground:
            logger.info(f"Skipping rating update for playground game {game.id}", extra={"game_id": str(game.id), "game_type": game.game_type.value})
            return

        try:
            # Extract game result from the final state
            game_result = env_type.extract_game_result(state)

            # Build agent mapping (player_id -> agent_id) and agent_version_mapping (agent_id -> agent_version_id)
            # Need to look up agent_id from agent_version_id
            agent_mapping: dict[PlayerId, AgentId] = {}
            agent_version_mapping: dict[AgentId, AgentVersionId] = {}
            for gp in game.game_players:
                # Get the agent version to find the parent agent_id
                agent_version = await self._agent_version_dao.get(db, gp.agent_version_id)
                if agent_version:
                    agent_mapping[gp.id] = agent_version.agent_id
                    agent_version_mapping[agent_version.agent_id] = gp.agent_version_id

            # Create rating update request - use agent_mapping keys as player_ids
            player_ids: list[PlayerId] = list(agent_mapping.keys())
            rating_request = GameRatingUpdateRequest(
                game_id=game.id, game_type=game.game_type, player_ids=player_ids, agent_mapping=agent_mapping, agent_version_mapping=agent_version_mapping
            )

            # Update ratings
            _ = await self._scoring_service.update_agent_ratings_after_game(db=db, request=rating_request, game_result=game_result)

            logger.info(
                f"Updated agent ratings for finished game {game.id}",
                extra={
                    "game_id": str(game.id),
                    "game_type": game.game_type.value,
                    "winner_id": str(game_result.winner_id) if game_result.winner_id else None,
                    "draw_reason": game_result.draw_reason,
                    "agent_count": len(agent_mapping),
                },
            )

        except Exception as e:
            # Log error with full details but don't fail the game completion
            logger.exception(
                f"Failed to update agent ratings for game {game.id}",
                extra={"game_id": str(game.id), "game_type": game.game_type.value, "error": str(e), "error_type": type(e).__name__},
            )

    async def create_empty_game(
        self,
        db: AsyncSession,
        game_type: GameType,
        config: BaseGameConfig,
        requesting_user_id: UserId,
        waiting_deadline: datetime | None = None,
        allows_midgame_joining: bool = False,
        min_players_required: int | None = None,
        max_players_allowed: int | None = None,
        is_playground: bool = False,
    ) -> Game:
        """Create an empty game in WAITING status without initializing game state.

        This is used by the matchmaking service to create a game that will
        be filled with players before being started.

        Args:
            db: Database session
            game_type: Type of game
            config: Game configuration
            requesting_user_id: User ID of the user creating the game
            waiting_deadline: Optional deadline for players to join
            allows_midgame_joining: Whether players can join after game starts
            min_players_required: Minimum number of players required
            max_players_allowed: Maximum number of players allowed
            is_playground: Whether this is a playground game

        Returns:
            Game object in WAITING status
        """
        logger.info(f"Creating empty game of type {game_type}")

        # Generate game_id first
        game_id = GameId(TSID.create())

        # Create game without players but with proper empty state from environment
        env = self._registry.create(game_type, config, analysis_handler=self._sqs_game_analysis_handler)
        event_collector = EventCollector[BaseGameEvent]()
        empty_state = env.new_game(game_id, event_collector)

        game = Game(
            id=game_id,
            game_type=game_type,
            state=empty_state.to_dict(mode="json"),  # Use proper empty state from environment
            config=config.to_dict(mode="json") if config else {},
            requesting_user_id=requesting_user_id,
            matchmaking_status=MatchmakingStatus.WAITING,
            waiting_deadline=waiting_deadline,
            allows_midgame_joining=allows_midgame_joining,
            min_players_required=min_players_required,
            max_players_allowed=max_players_allowed,
            is_playground=is_playground,
            version=0,
        )
        db.add(game)
        await db.commit()

        # Store initial events using CRUD
        await self._game_dao.add_events(db, game_id, event_collector.get_events())
        await db.commit()

        # Fetch game again to populate all object relations
        game = await self._game_dao.get(db, game_id)
        if not game:
            raise Errors.Generic.INTERNAL_ERROR.create(message=f"Game not found: {game_id}")

        logger.info(f"Created empty game {game_id} of type {game_type}")
        return game

    async def start_new_game(
        self,
        db: AsyncSession,
        game_type: GameType,
        config: BaseGameConfig,
        agent_ids: list[AgentVersionId],
        requesting_user_id: UserId,
        is_playground: bool = False,
        cleanup_playgrounds_for_user_id: UserId | None = None,
        custom_state_json: dict[str, Any] | None = None,
    ) -> Game:
        """Start a completely new game with all players provided upfront.

        Args:
            db: Database session
            game_type: Type of game
            config: Game configuration
            agent_ids: List of agent IDs
            requesting_user_id: User ID of the user creating the game (for LLM integration lookup)
            is_playground: Whether this is a playground game
            cleanup_playgrounds_for_user_id: User ID to cleanup other playgrounds for
            custom_state_json: Optional custom JSON state to initialize the game with

        Returns:
            Game object
        """
        logger.info(f"Starting new game with {len(agent_ids)} players{' from custom state' if custom_state_json else ''}")

        # Initialize game state from environment
        now = get_now()
        env = self._registry.create(game_type, config, self._sqs_game_analysis_handler)

        # Generate game_id first
        game_id = GameId(TSID.create())

        # First, create basic game state without players
        event_collector = EventCollector[BaseGameEvent]()
        state = env.new_game(game_id, event_collector)

        # Batch fetch all agent versions
        unique_agent_ids = set(agent_ids)
        agent_versions = await self._agent_version_dao.get_by_ids(db, unique_agent_ids)
        if len(agent_versions) != len(unique_agent_ids):
            missing_ids = [aid for aid in unique_agent_ids if aid not in agent_versions]
            raise Errors.Agent.NOT_FOUND.create(message=f"Agent versions not found: {missing_ids}", details={"missing_agent_version_ids": missing_ids})

        # Collect players
        game_players: list[GamePlayer] = []
        for agent_version_id in agent_ids:
            agent_version = agent_versions[agent_version_id]
            player_id = PlayerId(TSID.create())

            # Add player to the game state with agent version info
            env.join_player(state, player_id, event_collector, agent_version_id, agent_version.agent.name)

            game_player = GamePlayer(
                id=player_id,
                game_id=game_id,
                agent_version_id=agent_version_id,
                user_id=agent_version.user_id,
                env=game_type,
                join_time=now,
            )
            game_players.append(game_player)

        state = env.new_round(state, event_collector)

        # Create game, game_players and game_events records.
        _ = await self._game_dao.insert(
            db=db,
            game_id=game_id,
            game_type=env.types().type(),
            config=config,
            state=state,
            players=game_players,
            events=event_collector.get_events(),
            requesting_user_id=requesting_user_id,
            is_playground=is_playground,
        )

        # Fetch game again to populate all object relations like we expect them to be populated
        game = await self._game_dao.get(db, game_id)
        if not game:
            raise Errors.Generic.INTERNAL_ERROR.create(message=f"Game not found: {game_id}")

        # Apply custom state if provided
        if custom_state_json:
            game = await self._apply_custom_state(game, env, custom_state_json, db)

        # Optionally cleanup other playground games for this user
        if is_playground and cleanup_playgrounds_for_user_id:
            await self._game_dao.cancel_user_playgrounds_except(
                db,
                cleanup_playgrounds_for_user_id,
                exclude_game_id=game.id,
            )

        logger.info(f"Game {game.id} started successfully with {len(agent_ids)} participants")
        return game

    async def start_existing_game(
        self,
        db: AsyncSession,
        game_id: GameId,
    ) -> tuple[BaseGameState, list[BaseGameEvent]]:
        """Initialize an existing WAITING game and transition it to IN_PROGRESS.

        Args:
            db: Database session
            game_id: ID of the existing game to start

        Returns:
            Tuple of (state, events) for the started game
        """
        logger.info(f"Starting existing game {game_id}")

        # Load the existing game
        game = await self._game_dao.get(db, game_id)
        if not game:
            raise Errors.Game.NOT_FOUND.create(details={"game_id": game_id})

        if game.matchmaking_status != MatchmakingStatus.WAITING:
            raise Errors.Generic.INVALID_INPUT.create(message="Game is not in WAITING status", details={"game_id": game_id, "status": game.matchmaking_status})

        # Use existing config from the game
        if not game.config:
            raise Errors.Generic.INVALID_INPUT.create(message="Game has no existing config", details={"game_id": game_id})

        # Convert dict config to proper type
        env_class = self._registry.get(game.game_type)
        config_type = env_class.types().config_type()
        effective_config = config_type.model_validate(game.config)

        logger.info(
            "Starting existing game with config",
            game_id=game_id,
            game_type=game.game_type,
            config_from_db=game.config,
            effective_config=effective_config.model_dump(mode="json"),
        )

        # Initialize game state using shared logic
        game = await self._initialize_game_state(
            db=db,
            game=game,
            config=effective_config,
            custom_state_json=None,  # No custom state for existing games
        )

        # Parse the state and events from the game
        state = env_class.types().state_type().model_validate(game.state)

        # Parse events
        event_adapter = TypeAdapter(env_class.types().event_type())
        events = [event_adapter.validate_python(event.data) for event in game.events] if game.events else []

        logger.info(f"Game {game_id} started successfully")
        return state, events

    async def _apply_custom_state(
        self,
        game: Game,
        env: GenericGameEnv,
        custom_state_json: dict[str, Any],
        db: AsyncSession,
    ) -> Game:
        """Apply custom state JSON to a game."""
        logger.info(f"Applying custom state to game {game.id}")

        # Validate the custom state JSON using the environment's validation methods
        env_types = self._registry.get(game.game_type).types()
        try:
            # First validate the JSON structure using the environment's schema validation
            player_view = env_types.player_view_type().model_validate(custom_state_json)

            # Then apply domain-specific validation
            player_view = env.validate_test_json(player_view)

        except Exception as e:
            raise Errors.Generic.INVALID_INPUT.create(
                message=f"Invalid custom state JSON: {e}",
                details={"custom_state_json": custom_state_json},
            ) from e

        # Build a full state from the provided player view + common fields
        # Keep player order from env.new_game: first player is "white"/first to move in chess
        players_sorted = sorted(game.game_players, key=lambda gp: gp.join_time)
        player_ids = [gp.id for gp in players_sorted]
        assert len(player_ids) >= 2, "Expected at least 2 players"

        # Get current state to determine turn
        state = env_types.state_type().model_validate(game.state)

        # Determine current player id if chess-like: use side_to_move when present
        current_pid = state.current_player_id
        pv_dict = player_view.to_dict(mode="json")
        if "side_to_move" in pv_dict:
            # White moves => index 0, Black => index 1
            current_pid = player_ids[0] if pv_dict["side_to_move"] == "white" else player_ids[1]

        # Start from the base state (ensures required fields like players exist), then overlay the player view
        base_dict = state.to_dict(mode="json")

        # Apply custom state but preserve critical initialized fields
        new_state_dict: dict[str, Any] = {**base_dict}  # Start with base state

        # Apply custom state fields, but be selective about what we override
        for key, value in pv_dict.items():
            if key not in ["game_id", "game_type", "current_player_id", "turn"]:
                # For players field, we need special handling to preserve player IDs
                if key == "players":
                    new_state_dict[key] = self._merge_players_with_custom_state(
                        base_dict.get("players", []),
                        value,
                        game.game_type,
                    )
                else:
                    new_state_dict[key] = value

        # Set explicit authoritative fields that must not be overwritten
        new_state_dict.update(
            {
                "game_id": game.id,
                "game_type": game.game_type,
                "current_player_id": current_pid,
                "turn": state.turn,
            }
        )
        new_state = env_types.state_type().model_validate(new_state_dict)

        # Update the game state
        # Use mode="python" to keep snake_case for database storage
        game.state = new_state.to_dict(mode="python")
        game.turn = state.turn
        await self._game_dao.update_game(db, game)

        return game

    async def _initialize_game_state(
        self,
        db: AsyncSession,
        game: Game,
        config: BaseGameConfig,
        custom_state_json: dict[str, Any] | None = None,
    ) -> Game:
        """Initialize game state for an existing game and transition it to IN_PROGRESS.

        This is the shared logic used by both start_new_game and start_existing_game.
        """
        # Create the appropriate config for the game type
        env_class = self._registry.get(game.game_type)
        config_type = env_class.types().config_type()
        effective_config = config_type.model_validate(config)

        # Create the game environment with the config
        env = self._registry.create(game.game_type, effective_config, analysis_handler=self._sqs_game_analysis_handler)

        # Get all agent version IDs from game players
        agent_version_ids = await self._game_dao.get_player_agent_ids(db, game.id)

        if not agent_version_ids:
            logger.error("Cannot start game with no players", game_id=game.id)
            await self._game_dao.set_status(db=db, game_id=game.id, status=MatchmakingStatus.CANCELLED)
            await db.commit()
            raise Errors.Generic.INVALID_INPUT.create(message="Cannot start game with no players", details={"game_id": game.id})

        # Create initial game state
        event_collector = EventCollector[BaseGameEvent]()
        state = env.new_game(game.id, event_collector)

        # Fetch agent versions for player names
        agent_versions = await self._agent_version_dao.get_by_ids(db, set(agent_version_ids))

        # Get game players to add them to state with correct player IDs
        game_players_list = await self._game_dao.get_game_players(db, game.id)

        # Build mapping for quick lookup
        gp_by_id = {gp.id: gp for gp in game_players_list}
        original_player_ids = [gp.id for gp in game_players_list]

        # Let the environment decide ordering (e.g., Chess randomizes colors)
        ordered_player_ids = env.order_player_ids_for_start(original_player_ids)

        # Add each player to the game state in decided order
        for pid in ordered_player_ids:
            game_player = gp_by_id.get(pid)
            if game_player is None:
                continue
            agent_version = agent_versions.get(game_player.agent_version_id)
            if agent_version:
                try:
                    env.join_player(
                        state,
                        game_player.id,
                        event_collector,
                        game_player.agent_version_id,
                        agent_version.agent.name,
                    )
                except ValueError as e:
                    if "already has maximum number of players" in str(e):
                        logger.warning("Game already has maximum players, skipping player addition", game_id=game.id, player_id=game_player.id, error=str(e))
                        # Don't add this player, but continue with others
                        continue
                    # Re-raise other ValueError exceptions
                    raise

        # Start the first round
        state = env.new_round(state, event_collector)

        # Apply custom state if provided
        if custom_state_json:
            game = await self._apply_custom_state(game, env, custom_state_json, db)
            # Re-fetch the state after applying custom state
            state = env_class.types().state_type().model_validate(game.state)

        # Update game with initialized state and status via DAO
        game.state = state.to_dict(mode="json")
        game.turn = state.turn
        game.matchmaking_status = MatchmakingStatus.IN_PROGRESS
        game.started_at = get_now()
        await self._game_dao.update_game(db, game)

        # Store initial events using CRUD (no version bump)
        await self._game_dao.add_events(db, game.id, event_collector.get_events())

        logger.info(
            "Game state initialized and started",
            game_id=game.id,
            game_type=game.game_type,
            player_count=len(agent_version_ids),
        )

        return game

    def _merge_players_with_custom_state(
        self,
        base_players: list[Any],
        custom_players: list[Any],
        game_type: GameType,
    ) -> list[Any]:
        """Merge base players (with correct IDs) with custom player state.

        Args:
            base_players: Players from properly initialized game state
            custom_players: Players from custom state JSON
            game_type: Type of game to determine player structure

        Returns:
            Merged player list preserving IDs but applying custom state
        """
        if game_type == GameType.CHESS:
            # Chess players are just a list of PlayerId - use the base players
            return base_players
        if game_type == GameType.TEXAS_HOLDEM:
            # Poker players are complex objects - merge them carefully
            if not custom_players or len(custom_players) != len(base_players):
                # If custom players don't match expected count, use base players
                return base_players

            merged_players: list[Any] = []
            for i, base_player in enumerate(base_players):
                if i < len(custom_players):
                    custom_player = custom_players[i]
                    # Create merged player preserving the correct player_id from base
                    merged_player: dict[str, Any] = {**custom_player}
                    merged_player["player_id"] = base_player["player_id"]
                    merged_players.append(merged_player)
                else:
                    merged_players.append(base_player)
            return merged_players

        # For unknown game types, use base players to be safe
        return base_players  # type: ignore[unreachable]

    async def start_game_from_player_view(
        self,
        db: AsyncSession,
        game_type: GameType,
        config: BaseGameConfig,
        agent_ids: list[AgentVersionId],
        player_view: BaseGameStateView,
        requesting_user_id: UserId,
        is_playground: bool = False,
        cleanup_playgrounds_for_user_id: UserId | None = None,
    ) -> Game:
        """Create a new game from a validated player-view JSON.

        This is now a simple wrapper around start_game with custom_state_json.
        """
        # Convert the player view to JSON and use the enhanced start_game method
        custom_state_json = player_view.to_dict(mode="json")

        return await self.start_new_game(
            db=db,
            game_type=game_type,
            config=config,
            agent_ids=agent_ids,
            requesting_user_id=requesting_user_id,
            is_playground=is_playground,
            cleanup_playgrounds_for_user_id=cleanup_playgrounds_for_user_id,
            custom_state_json=custom_state_json,
        )

    async def delete_game(self, db: AsyncSession, game_id: GameId, requesting_user_id: UserId) -> None:
        """Cancel a game if the requesting user is a participant or if it's a playground game.

        Games are never actually deleted from the database - they are marked as CANCELLED
        to preserve history and statistics.

        For playground games, any authenticated user can cancel them since they're for testing.
        For regular games, only participants can cancel them.

        Raises:
            Errors.Game.NOT_FOUND (404) if the game does not exist
            Errors.Generic.ACCESS_DENIED (403) if the user is not authorized to cancel
        """
        game = await self._game_dao.get(db, game_id)
        if not game:
            raise Errors.Game.NOT_FOUND.create(details={"game_id": game_id})

        # Debug logging
        logger.info(
            "Checking game cancellation authorization",
            game_id=str(game_id),
            requesting_user_id=str(requesting_user_id),
            is_playground=game.is_playground,
            game_players_count=len(game.game_players),
            game_players_user_ids=[str(gp.user_id) if gp.user_id else "None" for gp in game.game_players],
        )

        # For playground games, allow any authenticated user to cancel
        # For regular games, check if user is a participant (user_id matches or user_id is None for system agents)
        if not game.is_playground:
            # Check if user is a participant in the game
            # Allow cancellation if:
            # 1. User's ID matches a game player's user_id, OR
            # 2. Game player has user_id=None (system agent) - in this case, allow any user to cancel
            is_participant = any(gp.user_id == requesting_user_id or gp.user_id is None for gp in game.game_players)

            if not is_participant:
                logger.error(
                    "Access denied - user not authorized to cancel game",
                    game_id=str(game_id),
                    requesting_user_id=str(requesting_user_id),
                    game_players_user_ids=[str(gp.user_id) if gp.user_id else "None" for gp in game.game_players],
                )
                raise Errors.Generic.ACCESS_DENIED.create(details={"game_id": game_id, "user_id": requesting_user_id})

        logger.info(f"Cancelling game {game_id}")
        await self._game_dao.set_status(db=db, game_id=game_id, status=MatchmakingStatus.CANCELLED)
        await db.commit()
        logger.info(f"Game {game_id} cancelled successfully")

    async def process_turn(
        self,
        db: AsyncSession,
        request_id: RequestId,
        game_id: GameId,
        player_id: PlayerId,
        turn: int,
        move_override: BasePlayerMoveData | None,
        is_playground: bool,
    ) -> tuple[BaseGameState, list[BaseGameEvent]]:
        """Process a turn in the game, supporting both SQS and non-SQS use cases.

        Args:
            db: Database session
            request_id: Request ID for tracking
            game_id: Game ID
            player_id: Player ID whose turn it is
            move_override: Optional move override for manual moves
            turn: Expected turn number for validation
            is_playground: Whether this is a playground game (opposite of production)

        Returns:
            Tuple of (new_state, new_events)
        """
        logger.info(f"Processing turn for game {game_id}{' with move override' if move_override else ''}")

        async with self._set_game_processing(db, request_id, game_id, turn) as game:
            env_type = self._registry.get(game.game_type)

            state = env_type.types().state_type().model_validate(game.state)

            if game.events is None:
                raise Errors.Generic.INTERNAL_ERROR.create(message=f"Game {game_id} has no events")

            # Use TypeAdapter to validate discriminated union events
            event_adapter = TypeAdapter(env_type.types().event_type())
            events = [event_adapter.validate_python(event.data) for event in game.events]

            if state.is_finished:
                logger.info(f"Game {game_id} is already finished")
                raise Errors.Game.ALREADY_FINISHED.create(details={"game_id": game_id})

            if state.current_player_id != player_id:
                raise Errors.Game.NOT_PLAYER_MOVE.create(details={"game_id": game_id, "player_id": player_id, "current_player_id": state.current_player_id})

            config_type = env_type.types().config_type()
            config = config_type.model_validate(game.config)

            env = env_type.create(config, self._sqs_game_analysis_handler)

            # Check for timeout before attempting to get agent move (chess only)
            event_collector = EventCollector[Any]()
            if env.types().type() == GameType.CHESS:
                from chess_game.chess_api import ChessState
                from chess_game.chess_env import ChessEnv

                if isinstance(env, ChessEnv) and isinstance(state, ChessState):
                    if env.check_timeout(state, event_collector):
                        logger.info(f"Game {game_id} ended due to timeout before agent could move")
                        # Update game state and return early
                        game.state = state.to_dict(mode="json")
                        game.turn = state.turn
                        game.matchmaking_status = MatchmakingStatus.FINISHED
                        await self._game_dao.update_game(db, game)
                        await self._game_dao.add_events(db, game.id, event_collector.get_events())

                        # Update agent ratings for timeout game
                        await self.update_ratings_for_finished_game(db, game, state, env_type)

                        await self._game_dao.set_leave_time_for_game(db, game_id)
                        return state, event_collector.get_events()

            # Get view and possible moves for current agent from env
            player_view = env.get_player_view(state, state.current_player_id, events)
            possible_moves = env.calc_possible_moves(state, state.current_player_id)

            # Get agent version for the current agent from game_players relationship
            current_game_player = next((gp for gp in game.game_players if gp.id == state.current_player_id), None)
            if not current_game_player:
                raise Errors.Generic.INTERNAL_ERROR.create(message=f"Game player not found for player_id: {state.current_player_id}")

            agent = await self._agent_version_dao.get(db, id=current_game_player.agent_version_id)
            if not agent:
                raise Errors.Agent.NOT_FOUND.create(message=f"Agent version not found: {current_game_player.agent_version_id}")

            # Use move override if provided, otherwise ask agent to provide a move
            if move_override:
                logger.info(f"Using move override for game {game_id}: {move_override}")

                # Validate move_override against the environment's move type
                try:
                    move_data: BasePlayerMoveData = env_type.types().player_move_type().model_validate(move_override)
                except Exception as e:
                    logger.info(f"Invalid move override format in game {game_id}: {e}")
                    # Silently ignore invalid move format for manual overrides
                else:
                    player_move: GenericPlayerMove = PlayerMove(player_id=player_id, data=move_data)

                    try:
                        # Only create and add reasoning event if the move is legal and applied
                        event_collector.add(
                            env_type.types().create_reasoning_event(
                                state.turn,
                                state.current_player_id,
                                AgentReasoning("Manual move override"),
                            )
                        )
                        env.apply_move(state, player_move, event_collector)
                    except ValueError:
                        # For manual overrides, ignore illegal moves gracefully without raising or logging errors
                        logger.info(f"Ignoring illegal manual move override in game {game_id}")
            else:
                # Ask agent to provide a move
                await self._apply_agent_move(
                    db=db,
                    env=env,
                    state=state,
                    event_collector=event_collector,
                    agent=agent,
                    player_view=player_view,
                    possible_moves=possible_moves,
                    game_id=game_id,
                    game=game,
                    requesting_user_id=game.requesting_user_id,
                )

            # Update game state
            game.state = state.to_dict(mode="json")
            game.turn = state.turn
            # Only mark as finished if the game state indicates it's finished
            if state.is_finished:
                game.matchmaking_status = MatchmakingStatus.FINISHED
            await self._game_dao.update_game(db, game)
            await self._game_dao.add_events(db, game.id, event_collector.get_events())

            # If the game is now finished, set leave_time for all participants and update ratings
            if state.is_finished:
                # Update agent ratings using the scoring service
                await self.update_ratings_for_finished_game(db, game, state, env_type)

                await self._game_dao.set_leave_time_for_game(db, game_id)
                logger.info(f"Game {game_id} finished - set leave_time for all participants and updated status")

            logger.info(f"Move processed successfully for game {game_id}")
            return state, event_collector.get_events()

    async def finalize_timeout(
        self,
        db: AsyncSession,
        request_id: RequestId,
        game_id: GameId,
        requesting_user_id: UserId,
        expected_player_id: PlayerId,
    ) -> tuple[BaseGameState, list[BaseGameEvent]]:
        """Finalize a game because the current player ran out of time."""

        async with self._set_game_processing(db, request_id, game_id, expected_turn=None) as game:
            if not game:
                raise Errors.Game.NOT_FOUND.create(details={"game_id": game_id})

            if game.matchmaking_status != MatchmakingStatus.IN_PROGRESS:
                raise Errors.Generic.INVALID_INPUT.create(
                    message="Game is not currently in progress",
                    details={"game_id": game_id, "status": game.matchmaking_status},
                )

            # Verify requester participates (or system player)
            is_participant = (
                any(gp.user_id == requesting_user_id or gp.user_id is None for gp in game.game_players) or game.requesting_user_id == requesting_user_id
            )
            if not is_participant:
                raise Errors.Generic.ACCESS_DENIED.create(details={"game_id": game_id, "user_id": requesting_user_id})

            env_type = self._registry.get(game.game_type)
            state = env_type.types().state_type().model_validate(game.state)

            if state.is_finished:
                raise Errors.Game.ALREADY_FINISHED.create(details={"game_id": game_id})

            if state.current_player_id != expected_player_id:
                raise Errors.Game.NOT_PLAYER_MOVE.create(
                    details={
                        "game_id": game_id,
                        "current_player_id": state.current_player_id,
                        "requested_player_id": expected_player_id,
                    }
                )

            config = env_type.types().config_type().model_validate(game.config)
            env = env_type.create(config, self._sqs_game_analysis_handler)
            event_collector = EventCollector[Any]()

            timeout_triggered = False
            winner_for_log: PlayerId | None = None
            draw_reason_for_log: str | None = None
            if env_type.types().type() == GameType.CHESS:
                from chess_game.chess_api import ChessState
                from chess_game.chess_env import ChessEnv

                chess_env = cast(ChessEnv, env)
                chess_state = cast(ChessState, state)

                # Log state before timeout check
                logger.info(
                    "About to check timeout",
                    game_id=str(game_id),
                    expected_player_id=str(expected_player_id),
                    current_player_id=str(chess_state.current_player_id),
                    last_timestamp_ms=chess_state.last_timestamp_ms,
                    remaining_time_ms=chess_state.remaining_time_ms,
                    is_finished=chess_state.is_finished,
                    disable_timers=chess_env.config.disable_timers,
                )

                timeout_triggered = chess_env.check_timeout(chess_state, event_collector)
                winner_for_log = chess_state.winner
                draw_reason_for_log = str(chess_state.draw_reason) if chess_state.draw_reason else None

                # Log result after timeout check
                logger.info(
                    "Timeout check completed",
                    game_id=str(game_id),
                    timeout_triggered=timeout_triggered,
                    is_finished_after_check=chess_state.is_finished,
                    winner=str(winner_for_log) if winner_for_log else None,
                    draw_reason=draw_reason_for_log,
                )
            else:
                raise Errors.Generic.INVALID_INPUT.create(
                    message="Timeout finalization not supported for this game type",
                    details={"game_id": game_id, "game_type": game.game_type},
                )

            if not timeout_triggered:
                logger.error(
                    "Timeout finalization failed - player still has time",
                    game_id=str(game_id),
                    expected_player_id=str(expected_player_id),
                    current_player_id=str(state.current_player_id),
                )
                raise Errors.Generic.INVALID_INPUT.create(
                    message="Active player still has time remaining",
                    details={"game_id": game_id, "player_id": expected_player_id},
                )

            game.state = state.to_dict(mode="json")
            game.turn = state.turn
            game.matchmaking_status = MatchmakingStatus.FINISHED
            await self._game_dao.update_game(db, game)
            if event_collector.get_events():
                await self._game_dao.add_events(db, game.id, event_collector.get_events())

            await self.update_ratings_for_finished_game(db, game, state, env_type)
            await self._game_dao.set_leave_time_for_game(db, game_id)

            logger.info(
                "Game finalized due to timeout",
                game_id=str(game_id),
                timed_out_player=str(expected_player_id),
                winner=str(winner_for_log) if winner_for_log else None,
                draw_reason=str(draw_reason_for_log) if draw_reason_for_log else None,
            )

            return state, event_collector.get_events()

    async def _apply_agent_move(
        self,
        db: AsyncSession,
        env: GenericGameEnv,
        state: BaseGameState,
        event_collector: EventCollector[Any],
        agent: AgentVersionResponse,
        player_view: BaseGameStateView,
        possible_moves: BasePlayerPossibleMoves | None,
        game_id: GameId,
        game: Game,
        requesting_user_id: UserId,
    ) -> None:
        """Get move from agent with timeout-based retry logic."""
        context = AgentExecutionContext(max_attempts=10)
        timeout_seconds = 300  # 5 minutes

        # Fetch tools for the agent
        tools = await self._tool_dao.get_by_ids(db, tool_ids=agent.tool_ids) if agent.tool_ids else []
        tools = [t for t in tools if t.validation_status == ToolValidationStatus.VALID]

        # Fetch LLM integration for the requesting user
        is_fast_mode = False  # Could be passed as parameter if needed
        provider = agent.fast_llm_provider if is_fast_mode else agent.slow_llm_provider
        llm_integration = await self._llm_integration_service.get_user_integration_by_provider_with_key(db, user_id=requesting_user_id, provider=provider)
        if not llm_integration:
            raise Errors.Llm.NOT_FOUND.create(
                f"No LLM integration configured for provider '{provider}' for this user. Please configure a default LLM integration before creating games."
            )

        async def _attempt_agent_execution() -> None:
            while context.attempts < context.max_attempts:
                # Check for chess timeout before each attempt
                if env.types().type() == GameType.CHESS:
                    from chess_game.chess_api import ChessState
                    from chess_game.chess_env import ChessEnv

                    if isinstance(env, ChessEnv) and isinstance(state, ChessState):
                        if env.check_timeout(state, event_collector):
                            logger.info(f"Game {game_id} ended due to timeout during agent execution")
                            return

                # Increment attempts counter at the start of each retry attempt
                context.attempts += 1
                try:
                    logger.info(f"Agent execution attempt {context.attempts}/{context.max_attempts}")

                    # Get opponent's rating for adaptive difficulty (generic for all game types)
                    opponent_rating = None
                    try:
                        # Find opponent player and get their rating from the players list
                        current_game_type = env.types().type()
                        for gp in game.game_players:
                            if gp.id != state.current_player_id:
                                # Get opponent's agent version to extract agent_id
                                opponent_agent = await self._agent_version_dao.get(db, gp.agent_version_id)
                                if opponent_agent:
                                    # Get statistics using the agent_id from the version
                                    statistics_response = await self._agent_statistics_dao.get_by_agent(db, opponent_agent.agent_id)
                                    if statistics_response:
                                        from shared_db.models.agent import AgentStatisticsData

                                        statistics_data = AgentStatisticsData.model_validate(statistics_response.statistics)
                                        if current_game_type in statistics_data.game_ratings:
                                            opponent_rating = int(statistics_data.game_ratings[current_game_type].rating)
                                            break
                    except Exception as e:
                        logger.warning(f"Failed to get opponent rating for adaptive difficulty: {e}")

                    # Check if this is the Brain bot and use Stockfish instead of LLM (chess-specific)
                    if env.types().type() == GameType.CHESS:
                        # Try to execute with Stockfish if this is the Brain bot
                        try:
                            stockfish_result = await execute_brain_bot_move(
                                agent=agent,
                                game_state=player_view,
                                possible_moves=possible_moves,
                                opponent_rating=opponent_rating,
                            )

                            if stockfish_result is not None:
                                # Brain bot execution successful - apply the move
                                logger.info(f"Brain bot (Stockfish) executed move on attempt {context.attempts}")

                                if stockfish_result.move_data:
                                    move_data = env.types().player_move_type().model_validate(stockfish_result.move_data)

                                    logger.info(
                                        "Brain bot move",
                                        game_id=game_id,
                                        player_id=state.current_player_id,
                                        agent_id=agent.id,
                                        attempt=context.attempts,
                                        move_type=type(stockfish_result.move_data).__name__,
                                        move_data=stockfish_result.move_data,
                                    )
                                    move: GenericPlayerMove = PlayerMove(player_id=state.current_player_id, data=move_data)

                                    # Store the moving player ID before apply_move changes it
                                    moving_player_id = state.current_player_id
                                    current_turn = state.turn

                                    # Apply the move first (this will increment turn and switch current_player_id)
                                    env.apply_move(state, move, event_collector)

                                    # Add reasoning event AFTER move is applied, using the original moving player
                                    event_collector.add(
                                        env.types().create_reasoning_event(
                                            current_turn,
                                            moving_player_id,
                                            stockfish_result.reasoning,
                                            tool_calls=[],  # Stockfish doesn't use tools
                                        ),
                                    )

                                    logger.info(f"Brain bot move applied successfully on attempt {context.attempts}")
                                    return
                                elif stockfish_result.exit:
                                    # Brain bot decided to exit (unlikely but handle it)
                                    logger.info(f"Brain bot decided to exit on attempt {context.attempts}")

                                    # Handle agent exiting
                                    finish_decision = env.on_player_left(state, state.current_player_id, event_collector)

                                    if finish_decision.value == "cancel":
                                        state.is_finished = True
                                        logger.info(f"Game {game_id} cancelled - no players remaining")
                                    elif finish_decision.value == "finish":
                                        state.is_finished = True
                                        remaining_players = [p.id for p in game.game_players if p.id != state.current_player_id]
                                        env.finish_due_to_forfeit(state, remaining_players, event_collector)
                                        logger.info(f"Game {game_id} finished - below minimum players")

                                    return
                        except Exception as e:
                            logger.exception(
                                "Brain bot Stockfish execution failed",
                                game_id=game_id,
                                agent_id=agent.id,
                                attempt=context.attempts,
                            )
                            raise Errors.Agent.INVALID_OUTPUT.create(
                                message="Brain bot could not produce a legal Stockfish move",
                                details={
                                    "game_id": str(game_id),
                                    "agent_id": str(agent.id),
                                    "attempt": context.attempts,
                                },
                                cause=e,
                            )

                    # Normal LLM-based agent execution
                    # For playground games, always use direct execution (not AgentCore)
                    if game.is_playground:
                        from app.services.agent_runner.direct_agent_runner import DirectAgentRunner

                        direct_runner = DirectAgentRunner(self._agent_execution_service)
                        result, updated_context = await direct_runner.invoke_agent(
                            agent=agent,
                            tools=tools,
                            llm_integration=llm_integration,
                            game_type=env.types().type(),
                            game_state=player_view,
                            possible_moves=possible_moves,
                            execution_context=context,
                            max_retries=2,  # Client-side retries
                            timeout_seconds=timeout_seconds,
                        )
                    else:
                        result, updated_context = await self._agent_runner.invoke_agent(
                            agent=agent,
                            tools=tools,
                            llm_integration=llm_integration,
                            game_type=env.types().type(),
                            game_state=player_view,
                            possible_moves=possible_moves,
                            execution_context=context,
                            max_retries=2,  # Client-side retries
                            timeout_seconds=timeout_seconds,
                        )

                    # Update the context with the returned one to preserve conversation history
                    context.messages = updated_context.messages
                    context.attempts = updated_context.attempts
                    context.failure = updated_context.failure

                    if result.exit:
                        # Agent decided to exit the game
                        logger.info(
                            "Agent exit",
                            game_id=game_id,
                            player_id=state.current_player_id,
                            agent_id=agent.id,
                            attempt=context.attempts,
                            chat_message=result.chat_message,
                        )

                        # Add reasoning event from top-level reasoning field
                        event_collector.add(
                            env.types().create_reasoning_event(
                                state.turn,
                                state.current_player_id,
                                result.reasoning,
                                tool_calls=result.tool_calls,
                            ),
                        )

                        # Add chat message event if present (required for exits, but validated in agent execution)
                        if result.chat_message:
                            event_collector.add(
                                env.types().create_chat_event(
                                    state.turn,
                                    state.current_player_id,
                                    result.chat_message,
                                )
                            )

                        # Handle agent exiting - call environment's on_player_left method
                        finish_decision = env.on_player_left(state, state.current_player_id, event_collector)

                        # Process the finish decision
                        if finish_decision.value == "cancel":
                            # No players left - cancel the game
                            state.is_finished = True
                            logger.info(f"Game {game_id} cancelled - no players remaining")
                        elif finish_decision.value == "finish":
                            # Below minimum players - finish the game
                            state.is_finished = True
                            remaining_players = [p.id for p in game.game_players if p.id != state.current_player_id]
                            env.finish_due_to_forfeit(state, remaining_players, event_collector)
                            logger.info(f"Game {game_id} finished - below minimum players")
                        # If "continue", the game continues with remaining players

                        logger.info(f"Agent exit processed successfully on attempt {context.attempts}")
                        return
                    else:
                        # Normal move processing
                        move_data = env.types().player_move_type().model_validate(result.move_data)
                        # Note: reasoning is stored in top-level result.reasoning, not in move_data.reasoning
                        # This avoids duplication in the response
                        logger.info(
                            "Agent move",
                            game_id=game_id,
                            player_id=state.current_player_id,
                            agent_id=agent.id,
                            attempt=context.attempts,
                            move_type=type(result.move_data).__name__,
                            move_data=result.move_data,
                            chat_message=result.chat_message,
                        )
                        move: GenericPlayerMove = PlayerMove(player_id=state.current_player_id, data=move_data)

                        # Store the moving player ID before apply_move changes it
                        moving_player_id = state.current_player_id
                        current_turn = state.turn

                        # Apply the move first (this will increment turn and switch current_player_id)
                        env.apply_move(state, move, event_collector)

                        # Add reasoning event AFTER move is applied, using the original moving player
                        logger.info(
                            "Creating reasoning event with tool calls",
                            game_id=game_id,
                            player_id=moving_player_id,
                            tool_calls_count=len(result.tool_calls),
                            tool_calls=result.tool_calls,
                        )
                        event_collector.add(
                            env.types().create_reasoning_event(
                                current_turn,
                                moving_player_id,
                                result.reasoning,
                                tool_calls=result.tool_calls,
                            ),
                        )

                        # Add chat message event if present (required for moves, but validated in agent execution)
                        if result.chat_message:
                            event_collector.add(
                                env.types().create_chat_event(
                                    current_turn,
                                    moving_player_id,
                                    result.chat_message,
                                )
                            )

                        logger.info(f"Move applied successfully on attempt {context.attempts}")

                        # Exit after successful move application
                        # TODO: In real games, this should continue to process the next player's turn
                        # For now (playground mode), we exit after one successful agent move
                        return

                except Exception as e:
                    # Do a dummy version update of the game. This also updates the updated_at and acts as a heartbeat.
                    await self._game_dao.update_game(db, game)

                    # Check if the error came from AgentExecutionService (no more retries)
                    if Errors.Agent.MAX_ITERATIONS_EXCEEDED.is_(e):
                        # Agent execution service failed with max iterations, use fallback
                        logger.warning("Agent execution service reached max iterations")
                        raise e

                    # Check for non-retryable errors
                    if not should_retry_exception(e):
                        logger.exception("Non-retryable error detected - not retrying")
                        raise e

                    # If the error came from applying the move (not from AgentExecutionService),
                    # we retry with the same ExecutionContext to give the agent another chance
                    logger.warning(f"Move application failed on attempt {context.attempts}, retrying with same context: {e!s}")
                    # Set the failure in context so AgentExecutionService can add it to chat messages
                    context.failure = f"Move failed: {e!s}"
                    # Continue the loop to retry

            # If we've exhausted all attempts, log and raise an error
            logger.error(f"Agent execution failed after {context.max_attempts} attempts")
            raise Errors.Agent.MAX_ITERATIONS_EXCEEDED.create(
                message=f"Agent execution failed after {context.max_attempts} retry attempts",
                details={"game_id": game_id, "agent_id": agent.id, "max_attempts": context.max_attempts},
            )

        try:
            # Run agent execution with timeout
            return await asyncio.wait_for(_attempt_agent_execution(), timeout=timeout_seconds)
        except TimeoutError:
            logger.exception(f"Agent execution timed out after {timeout_seconds} seconds")
        except Exception as e:
            # Check for non-retryable errors FIRST - these should not use fallback moves
            logger.exception("Error occurred during agent execution")
            if Errors.Game.CONCURRENT_PROCESSING.is_(e) or Errors.Game.TURN_ADVANCEMENT_CONFLICT.is_(e):
                raise e
            # if not should_retry_exception(e):
            #     raise e

        # If we get here, either timeout occurred or MAX_ITERATIONS_EXCEEDED was raised
        if env.types().type() == GameType.CHESS:
            # Chess has no fallback: opponent wins by forfeit
            from chess_game.chess_api import AgentForfeitEvent, ChessState, ForfeitReason, GameFinishedEvent

            opponent_ids = [gp.id for gp in game.game_players if gp.id != state.current_player_id]
            opponent_id = opponent_ids[0] if opponent_ids else None

            chess_state = cast(ChessState, state)
            chess_state.is_finished = True
            chess_state.winner = opponent_id
            chess_state.forfeit_reason = ForfeitReason.FAILED_TO_MOVE
            # Do NOT set draw_reason - forfeit is a win/loss, not a draw

            # Emit AgentForfeitEvent to record the forfeit
            event_collector.add(
                AgentForfeitEvent(
                    turn=chess_state.turn,
                    player_id=state.current_player_id,
                    reason="Failed to move within attempt limit",
                )
            )

            # Emit GameFinishedEvent to record the end of the game
            event_collector.add(
                GameFinishedEvent(
                    turn=chess_state.turn,
                    winner=opponent_id,
                    draw_reason=None,  # Forfeit is not a draw
                    forfeit_reason=ForfeitReason.FAILED_TO_MOVE,
                )
            )

            logger.info("Chess agent failed to move within attempt limit; awarding game to opponent by forfeit")

            # Update agent ratings for forfeit game
            await self.update_ratings_for_finished_game(db, game, state, type(env))

            return None

        # Default: use environment fallback move
        event_collector.add(
            env.types().create_reasoning_event(
                state.turn,
                state.current_player_id,
                AgentReasoning("Fallback move due to timeout or error"),
                tool_calls=[],
            ),
        )
        fallback_move_data: BasePlayerMoveData = env.error_fallback_move(state, event_collector, state.current_player_id)
        fallback_move: GenericPlayerMove = PlayerMove(player_id=state.current_player_id, data=fallback_move_data)
        env.apply_move(state, fallback_move, event_collector)
        logger.info("Applied fallback move successfully")
        return None

    @contextlib.asynccontextmanager
    async def _set_game_processing(
        self,
        db: AsyncSession,
        request_id: RequestId,
        game_id: GameId,
        expected_turn: int | None,
    ) -> AsyncGenerator[Game]:
        """Async context manager for game processing locks.

        Ensures processing lock is always released, even on exceptions.
        """
        game: Game | None = None
        try:
            game = await self._game_dao.start_processing(
                db,
                request_id,
                game_id,
                processing_timeout=GAME_PROCESSING_TIMEOUT,
                heartbeat_timeout=HEARTBEAT_TIMEOUT,
                expected_turn=expected_turn,
            )
            yield game
        except Exception:
            await db.rollback()
            raise
        finally:
            # Release the processing lock
            if game:
                await self._game_dao.finish_processing(db, request_id, game_id)
                await db.commit()

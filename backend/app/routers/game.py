"""Game API routes for managing turn-based games."""

from datetime import UTC, datetime
from typing import Annotated, Any, cast

from chess_game.chess_api import ChessPlaygroundOpponent, ChessSide, ChessState
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from game_api import BaseGameConfig, BaseGameEvent, BaseGameState, GameType, ReasoningEventMixin
from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import (
    get_brain_bot_agent_version,
    get_current_user,
    get_db,
    get_llm_integration_service,
    get_request_context,
    get_user_service,
)
from app.schemas.game import (
    ActiveGameResponse,
    CreateChessPlaygroundRequest,
    CreateGameRequest,
    CreateGameResponse,
    CreatePlaygroundRequest,
    ExecuteTurnRequest,
    FinalizeTimeoutRequest,
    GameConfigOptionsMapResponse,
    GameConfigOptionsResponse,
    GameEventResponse,
    GameHistoryListResponse,
    GameHistoryResponse,
    GamesCountResponse,
    GameStateResponse,
    TurnResultResponse,
    UserGameResult,
)
from app.service_container import Services
from app.services.game_env_registry import GameEnvRegistry
from app.services.game_service import GameService
from app.services.llm_integration_service import LLMIntegrationService
from app.services.long_poll_service import LongPollService
from app.services.user_service import UserService
from common.core.config_service import ConfigService
from common.core.request_context import RequestContext
from common.ids import AgentId, AgentVersionId, GameId, PlayerId
from common.utils.tsid import TSID
from common.utils.utils import get_logger
from shared_db.db import AsyncSessionLocal
from shared_db.models.game import MatchmakingStatus
from shared_db.models.game_enums import get_game_environment_metadata
from shared_db.schemas.user import CoinConsumeFailureReason, UserResponse

game_router = APIRouter()
logger = get_logger()
services = Services.instance()
game_service = GameService(services.game_dao)





@game_router.get("/games/active")
async def get_active_games(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    limit: int = Query(default=50, le=100),
) -> list[ActiveGameResponse]:
    """Get active games for the current user."""
    logger.info(f"Getting active games for user {current_user.id}")

    # Get user's active games (waiting or in progress)
    games = await services.game_dao.get_games_by_user(db=db, user_id=current_user.id, only_active=True, limit=limit)

    # Convert to response format
    active_games: list[ActiveGameResponse] = []
    now = datetime.now(UTC)

    for game in games:
        # Calculate time remaining for waiting games
        time_remaining_seconds = None
        if game.waiting_deadline and game.matchmaking_status == MatchmakingStatus.WAITING:
            time_remaining = (game.waiting_deadline - now).total_seconds()
            time_remaining_seconds = max(0, int(time_remaining))

        status_value = game.matchmaking_status

        # Compute user's color for chess
        user_color: ChessSide | None = None
        if game.game_type == GameType.CHESS:
            try:
                chess_state: ChessState = cast(ChessState, game_service.parse_game_state(game))
                user_player_ids_typed = [gp.id for gp in game.game_players if gp.user_id == current_user.id]
                if user_player_ids_typed:
                    if len(chess_state.players) > 0 and user_player_ids_typed[0] == chess_state.players[0]:
                        user_color = ChessSide.WHITE
                    elif len(chess_state.players) > 1 and user_player_ids_typed[0] == chess_state.players[1]:
                        user_color = ChessSide.BLACK
            except Exception:
                user_color = None

        # Get user's agent name
        user_agent_name: str | None = None
        user_game_player = next((gp for gp in game.game_players if gp.user_id == current_user.id), None)
        if user_game_player and user_game_player.agent_version and user_game_player.agent_version.agent:
            user_agent_name = user_game_player.agent_version.agent.name

        game_response = ActiveGameResponse(
            id=str(game.id),
            game_type=game.game_type,
            matchmaking_status=status_value,
            current_players=game.current_player_count,
            max_players=game.max_players_allowed or 0,
            min_players=game.min_players_required or 0,
            created_at=game.created_at.isoformat() if game.created_at else None,
            started_at=game.started_at.isoformat() if game.started_at else None,
            waiting_deadline=game.waiting_deadline.isoformat() if game.waiting_deadline else None,
            time_remaining_seconds=time_remaining_seconds,
            allows_midgame_joining=game.allows_midgame_joining,
            is_playground=game.is_playground,
            user_color=user_color,
            user_agent_name=user_agent_name,
        )

        logger.debug(
            "Returning active game",
            game_id=game.id,
            game_type=game.game_type,
            status_value=status_value,
            status_type=type(status_value).__name__,
            current_players=game.current_player_count,
        )

        active_games.append(game_response)

    logger.info(f"Returning {len(active_games)} active games for user {current_user.id}")
    return active_games


@game_router.get("/games/history")
async def get_game_history(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    game_type: str | None = Query(default=None),
) -> GameHistoryListResponse:
    """Get completed games history for the current user."""
    logger.info(f"Getting game history for user {current_user.id}")

    # Get user's completed games
    games = await services.game_dao.get_games_by_user(
        db=db,
        user_id=current_user.id,
        only_active=False,
        limit=limit,
        from_game_id=None,  # Simplified pagination - just use limit for now
    )

    # Filter by game type if specified
    if game_type:
        games = [game for game in games if game.game_type == game_type]

    # Convert to response format
    history_games: list[GameHistoryResponse] = []
    for game in games:
        # Skip active games, only include finished/cancelled
        if game.matchmaking_status in [MatchmakingStatus.WAITING, MatchmakingStatus.IN_PROGRESS]:
            continue

        # Get user's player IDs in this game (as strings for comparisons)
        user_player_ids = [str(gp.id) for gp in game.game_players if gp.user_id == current_user.id]

        # Use game environment registry to extract result information
        registry = GameEnvRegistry.instance()
        env_class = registry.get(game.game_type)

        # Parse state to proper Pydantic type and extract result
        # Skip games with empty/invalid state (shouldn't happen, but be defensive)
        try:
            parsed_state = game_service.parse_game_state(game)
            game_result = env_class.extract_game_result(parsed_state)
        except Exception as e:
            logger.warning(f"Failed to parse state for game {game.id}: {e}")
            continue

        # Convert result to response format
        winner_id = str(game_result.winner_id) if game_result.winner_id else None
        winners_ids = [str(w) for w in game_result.winners_ids]
        draw_reason = game_result.draw_reason
        final_chip_counts = {str(k): v for k, v in game_result.final_scores.items()} if game_result.final_scores else None

        # Determine user result generically using game_result (not game-specific logic)
        user_result: UserGameResult | None = None
        if parsed_state.is_finished and user_player_ids:
            user_player_id_str = user_player_ids[0]

            # Check if user won (single winner or multiple winners)
            if (winner_id and winner_id in user_player_ids) or (winners_ids and user_player_id_str in winners_ids):
                user_result = UserGameResult.WON
            # Check for draw
            elif draw_reason:
                user_result = UserGameResult.DRAW
            # Otherwise user lost or placed (for multi-player games)
            # For games with final scores (like poker), check if user has chips remaining
            elif game_result.final_scores:
                user_player_id = PlayerId(TSID(int(user_player_id_str)))
                user_chips = game_result.final_scores.get(user_player_id, 0)
                user_result = UserGameResult.LOST if user_chips == 0 else UserGameResult.PLACED
            else:
                # For games without scores (like chess), it's a loss
                user_result = UserGameResult.LOST

        # Get finished_at timestamp from leave_time of user's game_player
        finished_at = None
        user_agent_name: str | None = None
        for gp in game.game_players:
            if gp.user_id == current_user.id:
                if gp.leave_time:
                    finished_at = gp.leave_time.isoformat()
                if gp.agent_version and gp.agent_version.agent:
                    user_agent_name = gp.agent_version.agent.name
                break

        # Pass the Pydantic object directly - FastAPI will serialize it properly
        game_response = GameHistoryResponse(
            id=str(game.id),
            game_type=game.game_type,
            matchmaking_status=game.matchmaking_status,
            current_players=game.current_player_count,
            max_players=game.max_players_allowed or 0,
            created_at=game.created_at.isoformat() if game.created_at else None,
            started_at=game.started_at.isoformat() if game.started_at else None,
            finished_at=finished_at,
            is_playground=game.is_playground,
            has_events=bool(game.events),
            final_state=parsed_state,
            winner_id=str(winner_id) if winner_id else None,
            winners_ids=[str(w) for w in winners_ids] if winners_ids else [],
            draw_reason=draw_reason,
            final_chip_counts=final_chip_counts,
            user_result=user_result,
            user_agent_name=user_agent_name,
        )
        history_games.append(game_response)

    return GameHistoryListResponse(games=history_games, total=len(history_games), limit=limit, offset=offset)


@game_router.get("/agents/{agent_id}/games")
async def get_agent_games(
    agent_id: AgentId,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[UserResponse, Depends(get_current_user)],
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[GameHistoryResponse]:
    """Get game history for a specific agent (public endpoint)."""
    logger.info(f"Getting game history for agent {agent_id}")

    # Get the game environment registry
    registry = GameEnvRegistry.instance()

    # Get games where this agent participated
    games = await services.game_dao.get_games_by_agent(db, agent_id=agent_id, limit=limit, offset=offset)

    # Convert to GameHistoryResponse format (similar to get_game_history)
    history_games: list[GameHistoryResponse] = []
    for game in games:
        # Parse final state using the service
        final_state = game_service.parse_game_state(game)

        # Extract game result using the environment's extract_game_result method (extensible)
        env_class = registry.get(game.game_type)
        game_result = env_class.extract_game_result(final_state)

        # Convert game result to response format
        winner_id = str(game_result.winner_id) if game_result.winner_id else None
        winners_ids = [str(wid) for wid in game_result.winners_ids] if game_result.winners_ids else []
        draw_reason = game_result.draw_reason
        final_chip_counts = {str(k): v for k, v in game_result.final_scores.items()} if game_result.final_scores else None

        # Get finished_at timestamp from the latest leave_time of game_players
        finished_at = None
        agent_name: str | None = None
        if game.game_players:
            # Get the agent's game player entry
            agent_game_player = next((gp for gp in game.game_players if gp.agent_version.agent_id == agent_id), None)
            if agent_game_player:
                if agent_game_player.agent_version and agent_game_player.agent_version.agent:
                    agent_name = agent_game_player.agent_version.agent.name
                if agent_game_player.leave_time:
                    finished_at = agent_game_player.leave_time.isoformat()

            # If not found via agent, use latest leave_time as fallback
            if not finished_at:
                latest_leave_time = max((gp.leave_time for gp in game.game_players if gp.leave_time), default=None)
                if latest_leave_time:
                    finished_at = latest_leave_time.isoformat()

        # Pass the Pydantic object directly - FastAPI will serialize it properly
        game_response = GameHistoryResponse(
            id=str(game.id),
            game_type=game.game_type,
            matchmaking_status=game.matchmaking_status,
            current_players=game.current_player_count,
            max_players=game.max_players_allowed or 0,
            created_at=game.created_at.isoformat() if game.created_at else None,
            started_at=game.started_at.isoformat() if game.started_at else None,
            finished_at=finished_at,
            is_playground=game.is_playground,
            has_events=len(game.events) > 0,
            final_state=final_state,
            winner_id=winner_id,
            winners_ids=winners_ids,
            draw_reason=draw_reason,
            final_chip_counts=final_chip_counts,
            user_result=None,  # Not applicable for public agent endpoint
            user_agent_name=agent_name,
        )
        history_games.append(game_response)

    return history_games


@game_router.get("/games/discover")
async def discover_games(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    include_active: bool = True,
    include_ended: bool = True,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[ActiveGameResponse]:
    """Discover public/spectatable games for watching or replay.

    - Includes in-progress games for live watching
    - Optionally includes ended games for replay, controlled by feature flag
    """
    logger.info(f"Discovering games for user {current_user.id}")

    # Compute allowed statuses
    statuses: list[MatchmakingStatus] = []
    if include_active:
        statuses.append(MatchmakingStatus.IN_PROGRESS)

    allow_ended = ConfigService().get("features.allow_public_replay_ended_games", True)
    if include_ended and allow_ended:
        statuses += [MatchmakingStatus.FINISHED, MatchmakingStatus.CANCELLED]

    if not statuses:
        return []

    # Allowed game types by spectator policy (from environment registry)
    registry = GameEnvRegistry.instance()
    allowed_types = [gt for gt in GameType if registry.get(gt).types().supports_spectators()]

    # Fetch games
    games = await services.game_dao.find_discoverable_games(
        db=db,
        statuses=statuses,
        allowed_game_types=allowed_types,
        limit=limit,
        offset=offset,
    )

    # Convert to response
    responses: list[ActiveGameResponse] = []
    now = datetime.now(UTC)
    for game in games:
        time_remaining_seconds = None
        if game.waiting_deadline and game.matchmaking_status == MatchmakingStatus.WAITING:
            tr = (game.waiting_deadline - now).total_seconds()
            time_remaining_seconds = max(0, int(tr))

        responses.append(
            ActiveGameResponse(
                id=str(game.id),
                game_type=game.game_type,
                matchmaking_status=game.matchmaking_status,
                current_players=game.current_player_count,
                max_players=game.max_players_allowed or 0,
                min_players=game.min_players_required or 0,
                created_at=game.created_at.isoformat() if game.created_at else None,
                started_at=game.started_at.isoformat() if game.started_at else None,
                waiting_deadline=game.waiting_deadline.isoformat() if game.waiting_deadline else None,
                time_remaining_seconds=time_remaining_seconds,
                allows_midgame_joining=game.allows_midgame_joining,
                is_playground=game.is_playground,
            )
        )

    logger.info(f"Returning {len(responses)} discoverable games")
    return responses


@game_router.get("/games/{game_id}/events")
async def get_game_events(
    game_id: GameId,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> list[GameEventResponse]:
    """Get game events for replaying or spectating a game.

    Policy:
    - Non-participants: allowed only when the environment supports spectators (env-defined)
    - Reasoning visibility: never reveal opponent reasoning — users only see their own bots' reasoning
    """
    logger.info(f"Getting game events for game {game_id} by user {current_user.id}")

    # Fetch game
    game = await services.game_dao.get(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    # Spectator access policy
    is_participant = any(gp.user_id == current_user.id for gp in game.game_players)
    if not is_participant:
        registry = GameEnvRegistry.instance()
        env_cls = registry.get(game.game_type)
        if not env_cls.types().supports_spectators():
            raise HTTPException(status_code=403, detail="Access denied to this game")

    # Build quick lookup of current user's player IDs
    user_player_ids = {str(gp.id) for gp in game.game_players if gp.user_id == current_user.id}

    # Prepare types for identifying reasoning events
    events: list[GameEventResponse] = []
    registry = GameEnvRegistry.instance()
    env_cls = registry.get(game.game_type)
    types = env_cls.types()
    reasoning_type = types.reasoning_event_type()
    reasoning_adapter = TypeAdapter(reasoning_type)

    # Stream through events to preserve original ordering and indices
    for idx, db_event in enumerate(game.events):
        raw = db_event.data or {}
        data_out: dict[str, Any] = cast(dict[str, Any], raw)

        # If this is a reasoning event and not from the current user's bot, skip it entirely
        try:
            parsed_reasoning = reasoning_adapter.validate_python(data_out)
            typed_reasoning = cast(ReasoningEventMixin, parsed_reasoning)
            if str(typed_reasoning.player_id) not in user_player_ids:
                continue
        except Exception:
            # Not a reasoning event — include as-is
            pass

        # Normalize type to domain event type (e.g., 'move_played') rather than ORM class name
        normalized_type = str(data_out.get("type") or db_event.type)
        event_response = GameEventResponse(
            id=str(db_event.id),
            type=normalized_type,
            data=data_out,
            created_at=db_event.created_at.isoformat() if db_event.created_at else None,
            event_index=idx,
        )
        events.append(event_response)

    return events


@game_router.get("/games/config-options")
async def get_game_config_options(
    _current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> GameConfigOptionsMapResponse:
    """Get available configuration options for all game types."""
    logger.info("Getting game configuration options")

    registry = GameEnvRegistry.instance()
    config_options: dict[str, GameConfigOptionsResponse] = {}

    for game_type in GameType:
        try:
            env_class = registry.get(game_type)
            types = env_class.types()
            default_config = types.default_config()
            available_options = types.config_ui_options()

            config_options[game_type.value] = GameConfigOptionsResponse(
                game_type=game_type,
                default_config=default_config,
                available_options=available_options,
            )
        except Exception as e:
            logger.warning(f"Failed to get config options for {game_type}: {e}")
            continue

    return GameConfigOptionsMapResponse(config_options=config_options)


@game_router.get("/games/count")
async def get_user_games_count(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    game_type: Annotated[GameType | None, Query()] = None,
    only_active: Annotated[bool, Query()] = True,
) -> GamesCountResponse:
    """Lightweight count of user's games without loading events/state."""
    count = await services.game_dao.count_games_by_user(db, current_user.id, env=game_type, only_active=only_active)
    return GamesCountResponse(count=int(count))


@game_router.get("/games")
async def get_user_games(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    game_type: Annotated[GameType | None, Query(description="Filter by game type")] = None,
    only_active: Annotated[bool, Query(description="Only return active games")] = True,
    from_game_id: Annotated[GameId | None, Query(description="Get games after this game ID for pagination")] = None,
    limit: Annotated[int, Query(description="Maximum number of games to return", ge=1, le=100)] = 20,
) -> list[GameStateResponse[BaseGameState, BaseGameConfig, BaseGameEvent]]:
    """Get all games for the current user where their agents are participating."""
    logger.info(f"Getting games for user {current_user.id} with game_type={game_type}, only_active={only_active}, from_game_id={from_game_id}")

    games = await services.game_dao.get_games_by_user(
        db=db,
        user_id=current_user.id,
        env=game_type,
        from_game_id=from_game_id,
        limit=limit,
        only_active=only_active,
    )

    logger.info(f"Found {len(games)} games for user {current_user.id}")

    # Convert to response format with filtered reasoning events
    game_responses: list[GameStateResponse[BaseGameState, BaseGameConfig, BaseGameEvent]] = []
    for game in games:
        game_responses.append(game_service.build_generic_game_state_response(game, current_user.id))

    return game_responses


@game_router.post("/games", status_code=status.HTTP_201_CREATED)
async def create_game(
    request: CreateGameRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    llm_integration_service: Annotated[LLMIntegrationService, Depends(get_llm_integration_service)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> CreateGameResponse:
    """Create a new game."""
    logger.info(f"Creating new game of type {request.game_type} for user {current_user.id}")

    # Require user to have a default LLM integration before creating games
    _ = await llm_integration_service.require_user_default_integration(db, current_user.id)

    # Determine token cost from environment metadata
    env_meta = get_game_environment_metadata(request.game_type)
    token_cost = env_meta.real_game_token_cost_per_player

    # Try to consume tokens
    consumption_result = await user_service.try_consume_coins(db, current_user.id, token_cost)
    if not consumption_result.successful:
        if consumption_result.reason == CoinConsumeFailureReason.INSUFFICIENT_FUNDS:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Insufficient tokens. You need {token_cost} tokens to create a {request.game_type.value} game, but you only have {consumption_result.new_balance} tokens.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to consume tokens: {consumption_result.reason}",
        )

    logger.info(f"Consumed {token_cost} tokens for game creation. New balance: {consumption_result.new_balance}")

    registry = GameEnvRegistry.instance()
    env_class = registry.get(request.game_type)
    # Validate config against the environment's config type (do not override min/max here)
    config = env_class.types().config_type().model_validate(request.config)

    game = await services.game_manager.start_new_game(
        db=db,
        game_type=request.game_type,
        config=config,
        agent_ids=request.agent_ids,
        requesting_user_id=current_user.id,
    )

    return CreateGameResponse(
        game_id=game.id,
        message=f"Game {game.id} created successfully",
    )


@game_router.post("/games/playground", status_code=status.HTTP_201_CREATED)
async def create_playground(
    request: CreatePlaygroundRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    llm_integration_service: Annotated[LLMIntegrationService, Depends(get_llm_integration_service)],
) -> GameStateResponse[BaseGameState, BaseGameConfig, BaseGameEvent]:
    """Create a new Texas Hold'em playground where an agent plays against itself."""
    logger.info(f"Creating playground for agent {request.agent_id} with {request.num_players} players")

    # Require user to have a default LLM integration before creating games
    _ = await llm_integration_service.require_user_default_integration(db, current_user.id)

    registry = GameEnvRegistry.instance()
    env_class = registry.get(GameType.TEXAS_HOLDEM)

    # Set up playground config
    playground_config = request.config.copy()
    playground_config["min_players"] = request.num_players
    playground_config["max_players"] = request.num_players
    config = env_class.types().config_type().model_validate(playground_config)

    # Create agent list with the same agent repeated
    agent_ids = [request.agent_id] * request.num_players

    game = await services.game_manager.start_new_game(
        db=db,
        game_type=GameType.TEXAS_HOLDEM,
        config=config,
        agent_ids=agent_ids,
        requesting_user_id=current_user.id,
        is_playground=True,
        cleanup_playgrounds_for_user_id=current_user.id,
    )

    return game_service.build_generic_game_state_response(game, current_user.id)


@game_router.post("/games/playground/chess", status_code=status.HTTP_201_CREATED)
async def create_chess_playground(
    request: CreateChessPlaygroundRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    llm_integration_service: Annotated[LLMIntegrationService, Depends(get_llm_integration_service)],
    brain_bot_agent_version: Annotated[AgentVersionId, Depends(get_brain_bot_agent_version)],
) -> GameStateResponse[BaseGameState, BaseGameConfig, BaseGameEvent]:
    """Create a new Chess playground, optionally facing the Stockfish-powered bot."""
    logger.info(f"Creating chess playground for agent {request.agent_id} with opponent {request.opponent}")

    # Require user to have a default LLM integration before creating games
    _ = await llm_integration_service.require_user_default_integration(db, current_user.id)

    registry = GameEnvRegistry.instance()
    env_class = registry.get(GameType.CHESS)

    # Chess is strictly 2 players
    playground_config = request.config.copy()
    playground_config["min_players"] = 2
    playground_config["max_players"] = 2
    playground_config["disable_timers"] = True
    playground_config["playground_opponent"] = request.opponent
    playground_config["user_side"] = request.user_side
    config = env_class.types().config_type().model_validate(playground_config)

    agent_ids: list[AgentVersionId]
    if request.opponent == ChessPlaygroundOpponent.BRAIN:
        # Order agents based on user_side: first agent is white, second is black
        from chess_game.chess_api import ChessSide

        if request.user_side == ChessSide.WHITE:
            agent_ids = [request.agent_id, brain_bot_agent_version]
        else:
            agent_ids = [brain_bot_agent_version, request.agent_id]
    else:
        agent_ids = [request.agent_id, request.agent_id]

    game = await services.game_manager.start_new_game(
        db=db,
        game_type=GameType.CHESS,
        config=config,
        agent_ids=agent_ids,
        requesting_user_id=current_user.id,
        is_playground=True,
        cleanup_playgrounds_for_user_id=current_user.id,
    )

    return game_service.build_generic_game_state_response(game, current_user.id)


@game_router.delete("/games/{game_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_game(
    game_id: GameId,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> None:
    await services.game_manager.delete_game(db, game_id, current_user.id)


@game_router.get("/games/{game_id}")
async def get_game_state(
    game_id: GameId,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    request: Request,
    current_version: int | None = None,
    timeout: int = 30,
) -> GameStateResponse[BaseGameState, BaseGameConfig, BaseGameEvent]:
    """Get current game state with optional long polling.

    Args:
        game_id: The game ID
        current_version: If provided, will long-poll until version changes or timeout
        timeout: Maximum seconds to wait for changes (default 30, max 60)
    """
    # Limit timeout to reasonable values
    timeout = min(max(timeout, 1), 60)

    logger.debug(f"Getting game state for game {game_id}, current_version={current_version}, timeout={timeout}")

    # If no current_version provided, return immediately
    if current_version is None:
        game = await services.game_dao.get(db, game_id)
        if not game:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Game {game_id} not found",
            )

        response = game_service.build_generic_game_state_response(game, current_user.id)
        # Add matchmaking status for non-playground games
        response.matchmaking_status = game.matchmaking_status if not game.is_playground else None
        return response

    # Long polling: wait for version to change using LongPollService
    # Use a dedicated session for polling to avoid holding the request session
    lp = LongPollService()

    # Create a single polling session for the entire wait loop
    async with AsyncSessionLocal() as poll_session:

        async def _get_version() -> int | None:
            # Use the dedicated polling session
            return await services.game_dao.get_version(poll_session, game_id)

        async def _cancelled() -> bool:
            return await request.is_disconnected()

        # Wait until the version changes or timeout/cancellation
        _ = await lp.wait_for_change(
            initial_value=current_version,
            get_current_value=_get_version,
            timeout_s=timeout,
            interval_s=1.0,
            cancel_check=_cancelled,
        )

    # Either version changed or timeout reached; return current state
    game = await services.game_dao.get(db, game_id)
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game {game_id} not found",
        )

    response = game_service.build_generic_game_state_response(game, current_user.id)
    # Add matchmaking status for non-playground games
    response.matchmaking_status = game.matchmaking_status if not game.is_playground else None
    return response


@game_router.post("/games/{game_id}/turns")
async def execute_turn(
    game_id: GameId,
    request: ExecuteTurnRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    request_context: Annotated[RequestContext, Depends(get_request_context)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> TurnResultResponse[BaseGameState, BaseGameEvent]:
    """Execute a turn in the game."""
    logger.info(f"Executing turn for game {game_id} with request: {request.model_dump()}")

    # Fetch game to determine environment pricing
    game = await services.game_dao.get(db, game_id)
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game {game_id} not found",
        )

    env_meta = get_game_environment_metadata(game.game_type)

    # Consume tokens for playground move based on environment metadata
    token_cost = env_meta.playground_move_token_cost
    consumption_result = await user_service.try_consume_coins(db, current_user.id, token_cost)
    if not consumption_result.successful:
        if consumption_result.reason == CoinConsumeFailureReason.INSUFFICIENT_FUNDS:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Insufficient tokens. You need {token_cost} tokens to execute a move, but you only have {consumption_result.new_balance} tokens.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to consume tokens: {consumption_result.reason}",
        )

    logger.info(f"Consumed {token_cost} tokens for playground move. New balance: {consumption_result.new_balance}")

    # Process the turn and get new state and events
    new_state, new_events = await services.game_manager.process_turn(
        db,
        request_context.request_id,
        game_id,
        request.player_id,
        turn=request.turn,
        move_override=request.move_override,
        is_playground=True,
    )

    # Filter reasoning events from new_events to hide opponent reasoning
    filtered_new_events = game_service.filter_reasoning_events(new_events, game, current_user.id)

    logger.info(f"Turn executed successfully for game {game_id}")
    return TurnResultResponse[BaseGameState, BaseGameEvent](
        game_id=game_id,
        new_state=new_state,  # Pass the state object directly, not as dict
        new_events=filtered_new_events,  # Pass filtered event objects
        is_finished=new_state.is_finished,
        current_player_id=new_state.current_player_id,
        new_coins_balance=consumption_result.new_balance,  # Include updated balance for immediate UI update
    )


@game_router.post("/games/{game_id}/timeout")
async def finalize_game_timeout(
    game_id: GameId,
    request: FinalizeTimeoutRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    request_context: Annotated[RequestContext, Depends(get_request_context)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> TurnResultResponse[BaseGameState, BaseGameEvent]:
    logger.info(
        "Finalizing game due to timeout",
        game_id=str(game_id),
        player_id=str(request.player_id),
        user_id=str(current_user.id),
    )

    new_state, new_events = await services.game_manager.finalize_timeout(
        db=db,
        request_id=request_context.request_id,
        game_id=game_id,
        requesting_user_id=current_user.id,
        expected_player_id=request.player_id,
    )

    # Fetch game to filter reasoning events
    game = await services.game_dao.get(db, game_id)
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game {game_id} not found",
        )

    # Filter reasoning events from new_events to hide opponent reasoning
    filtered_new_events = game_service.filter_reasoning_events(new_events, game, current_user.id)

    return TurnResultResponse[BaseGameState, BaseGameEvent](
        game_id=game_id,
        new_state=new_state,
        new_events=filtered_new_events,
        is_finished=new_state.is_finished,
        current_player_id=new_state.current_player_id,
    )




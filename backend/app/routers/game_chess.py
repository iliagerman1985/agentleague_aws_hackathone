"""Chess-specific game routes (playground creation from FEN or move list)."""

from typing import Annotated, Any, Protocol, cast

from chess_game.chess_api import (
    ChessConfig,
    ChessEvent,
    ChessMoveData,
    ChessState,
    MovePlayedEvent,
)
from chess_game.chess_env import ChessEnv
from fastapi import APIRouter, Depends, HTTPException, status
from game_api import BaseGameEvent, EventCollector, GameId, GameType, PlayerId, PlayerMove
from pydantic import BaseModel, Field, TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_brain_bot_agent_version, get_current_user, get_db, get_llm_integration_service, get_sqs_game_analysis_handler
from app.schemas.game import ChessFromFENRequest, ChessFromMovesRequest, ChessFromStateRequest, GameStateResponse
from app.service_container import Services
from app.services.game_env_registry import GameEnvRegistry
from app.services.game_service import GameService
from app.services.llm_integration_service import LLMIntegrationService
from common.ids import AgentVersionId, PlayerId
from common.utils.utils import get_logger
from shared_db.schemas.user import UserResponse


# Local protocol to statically type objects that expose a JSON `data` field.
class _HasEventData(Protocol):
    data: dict[str, Any]


router = APIRouter()
logger = get_logger()
services = Services.instance()
game_service = GameService(services.game_dao)


# Conversion request/response models
class ConvertFENRequest(BaseModel):
    fen: str = Field(..., description="FEN string to convert")


class ConvertMovesRequest(BaseModel):
    moves: str = Field(..., description="Move list in SAN/PGN format to convert")


class ConvertStateResponse(BaseModel):
    state: dict[str, Any] = Field(..., description="Converted chess state view")


@router.post("/games/playground/chess/from_fen", status_code=status.HTTP_201_CREATED)
async def create_chess_from_fen(
    request: ChessFromFENRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    llm_integration_service: Annotated[LLMIntegrationService, Depends(get_llm_integration_service)],
    brain_bot_agent_version: Annotated[AgentVersionId, Depends(get_brain_bot_agent_version)],
) -> GameStateResponse[ChessState, ChessConfig, ChessEvent]:
    """Create a Chess playground from a FEN starting position."""
    logger.info(f"Creating chess playground from FEN with opponent {request.opponent} and agent {request.agent_id}")

    # Require user to have a default LLM integration before creating games
    _ = await llm_integration_service.require_user_default_integration(db, current_user.id)

    # Build chess playground config using service
    config = game_service.build_chess_playground_config(
        base_config=request.config or {},
        opponent=request.opponent,
        user_side=request.user_side,
    )

    # Parse FEN to a state view
    try:
        state_view = ChessEnv.state_view_from_fen(request.fen)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid FEN: {e}") from e

    # Derive agent IDs using service
    try:
        agent_ids = game_service.derive_chess_agent_ids(
            opponent=request.opponent,
            agent_id=request.agent_id,
            brain_bot_agent_version=brain_bot_agent_version,
            user_side=request.user_side,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    game = await services.game_manager.start_game_from_player_view(
        db=db,
        game_type=GameType.CHESS,
        config=config,
        agent_ids=agent_ids,
        player_view=state_view,
        requesting_user_id=current_user.id,
        is_playground=True,
        cleanup_playgrounds_for_user_id=current_user.id,
    )

    # Get the game with proper response using service
    return await game_service.get_game_state_response(db, game.id, current_user.id)


@router.post("/games/playground/chess/from_moves", status_code=status.HTTP_201_CREATED)
async def create_chess_from_moves(
    request: ChessFromMovesRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    llm_integration_service: Annotated[LLMIntegrationService, Depends(get_llm_integration_service)],
    brain_bot_agent_version: Annotated[AgentVersionId, Depends(get_brain_bot_agent_version)],
) -> GameStateResponse[ChessState, ChessConfig, ChessEvent]:
    """Create a Chess playground from a SAN/PGN-like move list."""
    logger.info(f"Creating chess playground from move list with opponent {request.opponent} and agent {request.agent_id}")

    # Require user to have a default LLM integration before creating games
    _ = await llm_integration_service.require_user_default_integration(db, current_user.id)

    # Build chess playground config using service
    config = game_service.build_chess_playground_config(
        base_config=request.config or {},
        opponent=request.opponent,
        user_side=request.user_side,
    )

    # Parse move list to a state view
    try:
        state_view = ChessEnv.state_view_from_moves(request.moves)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid move list: {e}") from e

    # Derive agent IDs using service
    try:
        agent_ids = game_service.derive_chess_agent_ids(
            opponent=request.opponent,
            agent_id=request.agent_id,
            brain_bot_agent_version=brain_bot_agent_version,
            user_side=request.user_side,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    game = await services.game_manager.start_game_from_player_view(
        db=db,
        game_type=GameType.CHESS,
        config=config,
        agent_ids=agent_ids,
        player_view=state_view,
        requesting_user_id=current_user.id,
        is_playground=True,
        cleanup_playgrounds_for_user_id=current_user.id,
    )

    # Get the game with proper response using service
    return await game_service.get_game_state_response(db, game.id, current_user.id)


@router.post("/games/playground/chess/from_state", status_code=status.HTTP_201_CREATED)
async def create_chess_from_state(
    request: ChessFromStateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    llm_integration_service: Annotated[LLMIntegrationService, Depends(get_llm_integration_service)],
    brain_bot_agent_version: Annotated[AgentVersionId, Depends(get_brain_bot_agent_version)],
) -> GameStateResponse[ChessState, ChessConfig, ChessEvent]:
    """Create a Chess playground from a JSON state view."""
    logger.info(f"Creating chess playground from state view with opponent {request.opponent} and agent {request.agent_id}")

    # Require user to have a default LLM integration before creating games
    _ = await llm_integration_service.require_user_default_integration(db, current_user.id)

    # Build chess playground config using service
    config = game_service.build_chess_playground_config(
        base_config=request.config or {},
        opponent=request.opponent,
        user_side=request.user_side,
    )

    # Parse state view JSON to a state view object
    registry = GameEnvRegistry.instance()
    env_class = registry.get(GameType.CHESS)
    try:
        state_view = env_class.types().player_view_type().model_validate(request.state_view)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid chess state view: {e}") from e

    # Derive agent IDs using service
    try:
        agent_ids = game_service.derive_chess_agent_ids(
            opponent=request.opponent,
            agent_id=request.agent_id,
            brain_bot_agent_version=brain_bot_agent_version,
            user_side=request.user_side,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    game = await services.game_manager.start_game_from_player_view(
        db=db,
        game_type=GameType.CHESS,
        config=config,
        agent_ids=agent_ids,
        player_view=state_view,
        requesting_user_id=current_user.id,
        is_playground=True,
        cleanup_playgrounds_for_user_id=current_user.id,
    )

    # Get the game with proper response using service
    return await game_service.get_game_state_response(db, game.id, current_user.id)








# Conversion endpoints for preview
@router.post("/games/chess/convert_fen")
async def convert_fen_to_state(
    request: ConvertFENRequest,
    _current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> ConvertStateResponse:
    """Convert a FEN string to a chess state view for preview."""
    try:
        state_view = ChessEnv.state_view_from_fen(request.fen)
        return ConvertStateResponse(state=state_view.model_dump())
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid FEN: {e}") from e


@router.post("/games/chess/convert_moves")
async def convert_moves_to_state(
    request: ConvertMovesRequest,
    _current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> ConvertStateResponse:
    """Convert a move list to a chess state view for preview."""
    try:
        state_view = ChessEnv.state_view_from_moves(request.moves)
        return ConvertStateResponse(state=state_view.model_dump())
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid moves: {e}") from e


@router.get("/games/chess/{game_id}/state_at_event/{event_index}")
async def get_state_at_event(
    game_id: GameId,
    event_index: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> GameStateResponse[ChessState, ChessConfig, ChessEvent]:
    """Reconstruct chess game state at a specific event index for replay.

    This endpoint replays all moves from the beginning up to the specified event index
    to reconstruct the exact board state at that point in the game.
    """
    logger.info(f"Reconstructing chess state at event {event_index} for game {game_id}")

    # Get the game with all relationships loaded
    game = await services.game_dao.get(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    # Verify user has access using service
    user_player_ids = game_service.get_user_player_ids(game, current_user.id)
    if not user_player_ids:
        raise HTTPException(status_code=403, detail="Access denied to this game")

    # Verify it's a chess game
    if game.game_type != GameType.CHESS:
        raise HTTPException(status_code=400, detail="This endpoint only supports chess games")

    # Parse config and get environment
    config_dict = game.config or {}
    chess_config = ChessConfig.model_validate(config_dict)
    env_registry = GameEnvRegistry.instance()

    # Get analysis handler from dependencies
    analysis_handler = get_sqs_game_analysis_handler()

    chess_env_generic = env_registry.create(GameType.CHESS, chess_config, analysis_handler)

    # Cast to ChessEnv for proper typing
    chess_env = cast(ChessEnv, chess_env_generic)

    # Create initial state
    event_collector: EventCollector[ChessEvent] = EventCollector()
    state: ChessState = chess_env.new_game(game_id, event_collector)

    # Parse all events first to determine player order
    event_adapter = TypeAdapter(ChessEvent)
    events_to_replay: list[ChessEvent] = [
        event_adapter.validate_python(ev.data)
        for ev in cast(
            "list[_HasEventData]",
            (game.events[: event_index + 1] if event_index >= 0 else []),
        )
    ]

    # Find the first move to determine which player is White (moves first)
    first_move_player_id: PlayerId | None = None
    for event in events_to_replay:
        if isinstance(event, MovePlayedEvent):
            first_move_player_id = event.player_id
            break

    # Add players in the correct order: White player first, then Black player
    # This ensures current_player_id matches the player making each move during replay
    players_for_replay = game_service.get_game_players_for_replay(game, first_move_player_id)

    for player_id, agent_version_id, agent_name in players_for_replay:
        chess_env.join_player(
            state=state,
            player_id=player_id,
            event_collector=event_collector,
            agent_version_id=agent_version_id,
            name=agent_name,
        )

    logger.info(f"Replaying {len(events_to_replay)} events up to index {event_index}")
    moves_applied = 0

    for idx, parsed_event in enumerate(events_to_replay):
        try:
            # Only apply move events - other events are informational
            if isinstance(parsed_event, MovePlayedEvent):
                move_data = ChessMoveData(
                    from_square=parsed_event.from_square,
                    to_square=parsed_event.to_square,
                    promotion=parsed_event.promotion,
                )
                player_move: PlayerMove[ChessMoveData] = PlayerMove[ChessMoveData](
                    player_id=parsed_event.player_id,
                    data=move_data,
                )

                # Apply the move to reconstruct state
                move_event_collector: EventCollector[ChessEvent] = EventCollector()
                chess_env.apply_move(state, player_move, move_event_collector)
                moves_applied += 1
                logger.info(f"Applied move {moves_applied}: {parsed_event.from_square} -> {parsed_event.to_square}")

        except Exception:
            logger.exception(f"Error replaying event at index {idx}")
            # Continue with other events even if one fails
            continue

    logger.info(f"Finished replaying. Applied {moves_applied} moves. Final board FEN: {state.board}")

    # Build response with reconstructed state
    players = game_service.build_player_info(game)

    # Get all events up to this point for the response
    all_events: list[ChessEvent] = events_to_replay

    # Filter reasoning events to hide opponent reasoning in replay mode
    # Cast to list[BaseGameEvent] for filtering, then cast back to list[ChessEvent]
    filtered_events_base = game_service.filter_reasoning_events(cast(list[BaseGameEvent], all_events), game, current_user.id)
    filtered_events = cast(list[ChessEvent], filtered_events_base)

    return GameStateResponse[ChessState, ChessConfig, ChessEvent](
        id=game.id,
        game_type=game.game_type,
        state=state,
        events=filtered_events,
        config=chess_config,
        version=game.version,
        players=players,
        is_playground=game.is_playground,
    )

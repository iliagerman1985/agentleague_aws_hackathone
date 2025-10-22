"""Poker-specific game routes (playground creation from pasted JSON state)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from game_api import GameType
from sqlalchemy.ext.asyncio import AsyncSession
from texas_holdem.texas_holdem_api import TexasHoldemConfig, TexasHoldemEvent, TexasHoldemState

from app.dependencies import get_current_user, get_db, get_llm_integration_service
from app.schemas.game import GameStateResponse, PokerFromStateRequest
from app.service_container import Services
from app.services.game_env_registry import GameEnvRegistry
from app.services.game_service import GameService
from app.services.llm_integration_service import LLMIntegrationService
from common.utils.utils import get_logger
from shared_db.schemas.user import UserResponse

router = APIRouter()
logger = get_logger()
services = Services.instance()
game_service = GameService(services.game_dao)


@router.post("/games/playground/poker/from_state", status_code=status.HTTP_201_CREATED)
async def create_poker_from_state(
    request: PokerFromStateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    llm_integration_service: Annotated[LLMIntegrationService, Depends(get_llm_integration_service)],
) -> GameStateResponse[TexasHoldemState, TexasHoldemConfig, TexasHoldemEvent]:
    """Create a Texas Hold'em playground from a validated player-view JSON state."""
    logger.info("Creating poker playground from pasted JSON state")

    # Require user to have a default LLM integration before creating games
    _ = await llm_integration_service.require_user_default_integration(db, current_user.id)

    registry = GameEnvRegistry.instance()
    env_class = registry.get(GameType.TEXAS_HOLDEM)

    # Clamp players to provided num_players
    num = max(2, int(request.num_players or 5))
    cfg_dict = dict(request.config or {})
    cfg_dict["min_players"] = num
    cfg_dict["max_players"] = num
    config = env_class.types().config_type().model_validate(cfg_dict)

    # Validate the provided state view against the authoritative schema
    try:
        view = env_class.types().player_view_type().model_validate(request.state_view)
        # Also pass through environment domain validator if available
        view = env_class.validate_test_json(view)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid poker state_view: {e}") from e

    agent_ids = [request.agent_id for _ in range(num)]

    game = await services.game_manager.start_game_from_player_view(
        db=db,
        game_type=GameType.TEXAS_HOLDEM,
        config=config,
        agent_ids=agent_ids,
        player_view=view,
        requesting_user_id=current_user.id,
        is_playground=True,
        cleanup_playgrounds_for_user_id=current_user.id,
    )

    # Build response using service
    return game_service.build_poker_game_state_response(game, current_user.id)

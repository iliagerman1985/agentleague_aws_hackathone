"""Game matching API routes."""

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from game_api import BaseGameConfig
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.schemas.game_matching import (
    JoinMatchmakingRequest,
    JoinMatchmakingResponse,
    LeaveMatchmakingRequest,
    LeaveMatchmakingResponse,
    MatchmakingStatusResponse,
)
from app.service_container import Services
from app.services.game_env_registry import GameEnvRegistry
from common.utils.utils import get_logger
from shared_db.models.game_enums import get_game_environment_metadata
from shared_db.schemas.user import UserResponse

game_matching_router = APIRouter()
logger = get_logger()
services = Services.instance()

MAX_MATCHMAKING_STATUS_TIMEOUT_SECONDS = 60


@game_matching_router.post("/matchmaking/join", status_code=status.HTTP_201_CREATED)
async def join_matchmaking(
    request: JoinMatchmakingRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> JoinMatchmakingResponse:
    """Join matchmaking queue for a game type."""
    # Validate config against the correct type for the game
    validated_config: BaseGameConfig | None = None
    if request.config:
        registry = GameEnvRegistry.instance()
        env_class = registry.get(request.game_type)
        config_type = env_class.types().config_type()
        # Validate the dict config against the correct type
        validated_config = config_type.model_validate(request.config)
        logger.info(
            "Validated matchmaking config",
            game_type=request.game_type,
            config=validated_config.model_dump(mode="json"),
        )

    game = await services.game_matching_service.join_matchmaking(
        db=db,
        user_id=current_user.id,
        game_type=request.game_type,
        agent_version_id=request.agent_version_id,
        config=validated_config,
    )

    env_metadata = get_game_environment_metadata(request.game_type)

    return JoinMatchmakingResponse(
        game_id=game.id,
        matchmaking_status=game.matchmaking_status,
        current_players=game.current_player_count,
        min_players=env_metadata.min_players,
        max_players=env_metadata.max_players,
        waiting_deadline=game.waiting_deadline,
        allows_midgame_joining=game.allows_midgame_joining,
    )


@game_matching_router.get("/matchmaking/status")
async def get_matchmaking_status(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    timeout: int = MAX_MATCHMAKING_STATUS_TIMEOUT_SECONDS,
) -> MatchmakingStatusResponse:
    """Get current matchmaking status for the user with long polling support.

    Note: This endpoint does NOT hold a database connection for the entire request.
    The service creates short-lived sessions for each poll iteration to prevent
    connection pool exhaustion during long-polling.
    """

    async def cancelled() -> bool:
        return await request.is_disconnected()

    return await services.game_matching_service.get_status_long_poll(current_user.id, timeout, cancelled)


@game_matching_router.post("/matchmaking/leave")
async def leave_matchmaking(
    http_request: Request,
    payload: LeaveMatchmakingRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> LeaveMatchmakingResponse:
    """Leave matchmaking queue."""
    if await http_request.is_disconnected():
        logger.info(
            "Client disconnected before leave matchmaking request processed",
            user_id=current_user.id,
            game_id=payload.game_id,
        )
        raise asyncio.CancelledError()

    try:
        result = await services.game_matching_service.leave_matchmaking(
            db=db,
            user_id=current_user.id,
            game_id=payload.game_id,
        )
    except asyncio.CancelledError:
        logger.info(
            "Leave matchmaking cancelled by client",
            user_id=current_user.id,
            game_id=payload.game_id,
        )
        raise

    return result

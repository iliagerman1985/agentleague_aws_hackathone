"""Game matching service for multiplayer matchmaking."""

from collections.abc import Awaitable, Callable
from datetime import timedelta

from game_api import BaseGameConfig, BaseGameEvent, BaseGameState, EventCollector, FinishDecision, GameAnalysisHandler, GameType, GenericGameEnv
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.game_matching import LeaveMatchmakingResponse, MatchmakingStatusResponse
from app.services.game_env_registry import GameEnvRegistry
from app.services.game_manager import GameManager
from app.services.sqs_game_turn_handler import SqsGameTurnHandler
from common.core.app_error import Errors
from common.ids import AgentVersionId, GameId, UserId
from common.utils.json_model import JsonModel
from common.utils.utils import get_logger, get_now
from shared_db.crud.agent import AgentVersionDAO
from shared_db.crud.game import GameDAO, JoinResult
from shared_db.crud.user import UserDAO
from shared_db.db import AsyncSessionLocal
from shared_db.models.game import Game, MatchmakingStatus
from shared_db.models.game_enums import get_game_environment_metadata
from shared_db.schemas.user import CoinConsumeFailureReason

logger = get_logger()


class PlayerInfoForLogging(JsonModel):
    """Player information for logging purposes."""

    player_id: str = Field(..., description="Player ID")
    username: str = Field(..., description="Username of the player")
    agent_name: str = Field(..., description="Agent name")
    leave_time: str | None = Field(default=None, description="Leave time if player has left")


class RemainingPlayerInfoForLogging(JsonModel):
    """Remaining player information for logging purposes."""

    player_id: str = Field(..., description="Player ID")
    username: str = Field(..., description="Username of the player")
    agent_name: str = Field(..., description="Agent name")


class GameMatchingService:
    """Service for handling game matchmaking operations."""

    def __init__(
        self,
        game_dao: GameDAO,
        agent_dao: AgentVersionDAO,
        game_manager: GameManager,
        user_dao: UserDAO,
        sqs_game_turn_handler: SqsGameTurnHandler,
        analysis_handler: GameAnalysisHandler,
    ) -> None:
        self.game_dao = game_dao
        self.agent_dao = agent_dao
        self.game_manager = game_manager
        self.user_dao = user_dao
        self.sqs_game_turn_handler = sqs_game_turn_handler
        self.analysis_handler = analysis_handler

    async def join_matchmaking(
        self,
        db: AsyncSession,
        game_type: GameType,
        user_id: UserId,
        agent_version_id: AgentVersionId,
        config: BaseGameConfig | None = None,
    ) -> Game:
        """Join matchmaking queue for a game type.

        Args:
            db: Database session
            game_type: Type of game to join
            user_id: User ID
            agent_version_id: Agent version to use
            config: Optional game configuration overrides

        Returns:
            Game object (either existing or newly created)

        Raises:
            AppError: If agent already in queue or other validation errors
        """
        # Validate that the agent version exists
        agent_version = await self.agent_dao.get(db, agent_version_id)
        if not agent_version:
            raise Errors.Agent.NOT_FOUND.create(
                message="Agent version not found",
                details={"agent_version_id": agent_version_id},
            )

        # Validate that the agent's game environment matches the game type
        if agent_version.game_environment != game_type:
            raise Errors.Agent.INVALID_ENVIRONMENT.create(
                message=f"Agent is designed for {agent_version.game_environment}, cannot join {game_type} game",
                details={
                    "agent_version_id": agent_version_id,
                    "agent_environment": agent_version.game_environment,
                    "game_type": game_type,
                },
            )

        # Get game environment metadata
        env_metadata = get_game_environment_metadata(game_type)

        # Try to find an open game
        open_games = await self.game_dao.find_open_games(
            db=db,
            game_type=game_type,
            exclude_user_id=user_id,  # Don't join games where user already has an agent
        )

        if open_games:
            # Attempt to join one of the open games atomically
            for candidate in open_games:
                logger.info(
                    "Attempting atomic join for existing game",
                    user_id=user_id,
                    game_id=candidate.id,
                    agent_version_id=agent_version_id,
                )

                result, _, new_count = await self.game_dao.join_game_atomically(
                    db=db,
                    game_id=candidate.id,
                    agent_version_id=agent_version_id,
                    user_id=user_id,
                    env=game_type,
                    is_system_player=False,
                )

                if result == JoinResult.FULL:
                    # Try next candidate
                    continue

                # Either joined or already joined; commit changes and refresh
                await db.commit()
                await self._refresh_game_for_response(db=db, game=candidate)

                if result == JoinResult.ALREADY_JOINED:
                    logger.info(
                        "Agent already present in candidate game, returning",
                        user_id=user_id,
                        game_id=candidate.id,
                        agent_version_id=agent_version_id,
                        current_players=candidate.current_player_count,
                    )
                    return candidate

                # Joined successfully
                # Charge tokens for this join (each non-system player pays)
                token_cost = env_metadata.real_game_token_cost_per_player
                consumption = await self.user_dao.try_consume_coins(db, user_id, token_cost)
                if not consumption.successful:
                    if consumption.reason == CoinConsumeFailureReason.INSUFFICIENT_FUNDS:
                        # Revert the join and remove the player from the game
                        await self.game_dao.set_leave_time(
                            db=db,
                            game_id=candidate.id,
                            agent_version_id=agent_version_id,
                        )
                        updated = await self.game_dao.update_player_count(db=db, game_id=candidate.id)
                        candidate.current_player_count = updated
                        await db.commit()
                        await self._refresh_game_for_response(db=db, game=candidate)
                        raise Errors.Generic.INVALID_INPUT.create(
                            message=f"Insufficient tokens. You need {token_cost} tokens to join a {game_type.value} game, but you only have {consumption.new_balance} tokens.",
                            http_status=402,
                        )
                    raise Errors.Generic.INTERNAL_ERROR.create(message=f"Failed to consume tokens: {consumption.reason}")

                should_start_game = new_count >= env_metadata.min_players
                logger.info(
                    "Player joined game - checking if ready to start",
                    game_id=candidate.id,
                    current_player_count=new_count,
                    min_players_required=env_metadata.min_players,
                    should_start=should_start_game,
                )

                if should_start_game:
                    await self.sqs_game_turn_handler.start_existing_game(db=db, game_id=candidate.id)
                    await self._refresh_game_for_response(db=db, game=candidate)

                return candidate

        # No open games, create a new one
        logger.info(
            "Creating new matchmaking game",
            user_id=user_id,
            game_type=game_type,
            agent_version_id=agent_version_id,
        )

        waiting_deadline = get_now() + timedelta(seconds=env_metadata.waiting_time_seconds)

        # Create a new empty WAITING game via GameManager
        # Get default config from the game environment registry if none provided
        if not config:
            registry = GameEnvRegistry.instance()
            env_class = registry.get(game_type)
            config = env_class.types().default_config()

        logger.info(
            "Creating matchmaking game with config",
            game_type=game_type,
            config=config.model_dump(mode="json"),
        )

        game = await self.game_manager.create_empty_game(
            db=db,
            game_type=game_type,
            config=config,
            requesting_user_id=user_id,
            waiting_deadline=waiting_deadline,
            allows_midgame_joining=env_metadata.supports_midgame_joining,
            min_players_required=env_metadata.min_players,
            max_players_allowed=env_metadata.max_players,
        )

        # Add the first player to the game
        result, _, new_count = await self.game_dao.join_game_atomically(
            db=db,
            game_id=game.id,
            agent_version_id=agent_version_id,
            user_id=user_id,
            env=game_type,
            is_system_player=False,
        )

        if result != JoinResult.JOINED:
            # This should not happen since we just created the game
            logger.error(
                "Failed to add first player to newly created game",
                game_id=game.id,
                agent_version_id=agent_version_id,
                result=result,
            )
            raise Errors.Generic.INTERNAL_ERROR.create(
                message="Failed to add first player to newly created game",
                details={
                    "game_id": game.id,
                    "agent_version_id": agent_version_id,
                    "result": result,
                },
            )

        # Charge tokens for the first player who just joined (each non-system player pays)
        token_cost = env_metadata.real_game_token_cost_per_player
        consumption = await self.user_dao.try_consume_coins(db, user_id, token_cost)
        if not consumption.successful:
            # Revert join and cancel the newly created game
            await self.game_dao.set_leave_time(
                db=db,
                game_id=game.id,
                agent_version_id=agent_version_id,
            )
            await self.game_dao.set_status(db=db, game_id=game.id, status=MatchmakingStatus.CANCELLED)
            await db.commit()
            await self._refresh_game_for_response(db=db, game=game)
            if consumption.reason == CoinConsumeFailureReason.INSUFFICIENT_FUNDS:
                raise Errors.Generic.INVALID_INPUT.create(
                    message=f"Insufficient tokens. You need {token_cost} tokens to join a {game_type.value} game, but you only have {consumption.new_balance} tokens.",
                    http_status=402,
                )
            raise Errors.Generic.INTERNAL_ERROR.create(message=f"Failed to consume tokens: {consumption.reason}")

        await db.commit()
        await self._refresh_game_for_response(db=db, game=game)

        logger.info(
            "Created new matchmaking game",
            game_id=game.id,
            waiting_deadline=waiting_deadline,
            current_player_count=game.current_player_count,
            min_players_required=env_metadata.min_players,
        )
        return game

    async def get_status_long_poll(
        self,
        user_id: UserId,
        timeout: int,
        cancel_check: Callable[[], Awaitable[bool]] | None = None,
    ) -> MatchmakingStatusResponse:
        """Get the current user's matchmaking status with long polling.

        Creates a new DB session for each poll iteration to avoid holding
        connections for the entire long-poll duration (30-60 seconds).
        This prevents connection pool exhaustion.
        """
        poll_timeout = max(1, min(timeout, 60))
        start_time = get_now()
        max_wait = timedelta(seconds=poll_timeout)
        poll_interval = 1

        initial_game: GameId | None = None
        initial_status: MatchmakingStatus | None = None
        current_game: Game | None = None

        import asyncio as _asyncio

        try:
            while (get_now() - start_time) < max_wait:
                if cancel_check and await cancel_check():
                    raise _asyncio.CancelledError()

                # Create a new session for this poll iteration
                async with AsyncSessionLocal() as db:
                    user_games = await self.game_dao.get_games_by_user(
                        db=db,
                        user_id=user_id,
                        only_active=True,
                        limit=1,
                    )

                    if not user_games:
                        # No active games; return empty status
                        return MatchmakingStatusResponse(
                            game_id=None,
                            game_type=None,
                            matchmaking_status=None,
                            current_players=0,
                            min_players=0,
                            max_players=0,
                            waiting_deadline=None,
                            time_remaining_seconds=None,
                        )

                    current_game = user_games[0]

                    # Return immediately for any state other than WAITING
                    if current_game.matchmaking_status != MatchmakingStatus.WAITING:
                        if current_game.matchmaking_status != MatchmakingStatus.IN_PROGRESS:
                            # Terminal states => clear client UI
                            return MatchmakingStatusResponse(
                                game_id=None,
                                game_type=None,
                                matchmaking_status=None,
                                current_players=0,
                                min_players=0,
                                max_players=0,
                                waiting_deadline=None,
                                time_remaining_seconds=None,
                            )

                        # IN_PROGRESS => provide full info
                        env_metadata = get_game_environment_metadata(current_game.game_type)
                        time_remaining = None
                        if current_game.waiting_deadline:
                            time_remaining = max(0, int((current_game.waiting_deadline - get_now()).total_seconds()))

                        return MatchmakingStatusResponse(
                            game_id=current_game.id,
                            game_type=current_game.game_type,
                            matchmaking_status=current_game.matchmaking_status,
                            current_players=current_game.current_player_count,
                            min_players=env_metadata.min_players,
                            max_players=env_metadata.max_players,
                            waiting_deadline=current_game.waiting_deadline,
                            time_remaining_seconds=time_remaining,
                        )

                    if initial_game is None:
                        initial_game = current_game.id
                        initial_status = current_game.matchmaking_status

                    status_changed = current_game.matchmaking_status != initial_status or current_game.id != initial_game

                    if status_changed:
                        env_metadata = get_game_environment_metadata(current_game.game_type)
                        time_remaining = None
                        if current_game.waiting_deadline:
                            time_remaining = max(0, int((current_game.waiting_deadline - get_now()).total_seconds()))

                        return MatchmakingStatusResponse(
                            game_id=current_game.id,
                            game_type=current_game.game_type,
                            matchmaking_status=current_game.matchmaking_status,
                            current_players=current_game.current_player_count,
                            min_players=env_metadata.min_players,
                            max_players=env_metadata.max_players,
                            waiting_deadline=current_game.waiting_deadline,
                            time_remaining_seconds=time_remaining,
                        )
                # Session is automatically closed here

                await _asyncio.sleep(poll_interval)
        except _asyncio.CancelledError:
            logger.info("Matchmaking status poll cancelled by client", user_id=user_id)
            raise

        # Timeout reached; return current state if available
        if current_game:
            env_metadata = get_game_environment_metadata(current_game.game_type)
            time_remaining = None
            if current_game.waiting_deadline:
                time_remaining = max(0, int((current_game.waiting_deadline - get_now()).total_seconds()))

            return MatchmakingStatusResponse(
                game_id=current_game.id,
                game_type=current_game.game_type,
                matchmaking_status=current_game.matchmaking_status,
                current_players=current_game.current_player_count,
                min_players=env_metadata.min_players,
                max_players=env_metadata.max_players,
                waiting_deadline=current_game.waiting_deadline,
                time_remaining_seconds=time_remaining,
            )

        return MatchmakingStatusResponse(
            game_id=None,
            game_type=None,
            matchmaking_status=None,
            current_players=0,
            min_players=0,
            max_players=0,
            waiting_deadline=None,
            time_remaining_seconds=None,
        )

    async def leave_matchmaking(
        self,
        db: AsyncSession,
        user_id: UserId,
        game_id: GameId,
    ) -> LeaveMatchmakingResponse:
        """Leave matchmaking queue.

        Args:
            db: Database session
            user_id: User ID
            game_id: Game ID to leave

        Returns:
            LeaveMatchmakingResponse with status information

        Raises:
            AppError: If game not found
        """
        game = await self.game_dao.get(db=db, game_id=game_id)
        if not game:
            raise Errors.Game.NOT_FOUND.create(
                message="Game not found",
                details={"game_id": game_id},
            )

        # Find user's player in this game
        user_player = next(
            (gp for gp in game.game_players if gp.user_id == user_id and gp.leave_time is None),
            None,
        )

        if not user_player:
            # User is not in the game (either never joined or already left)
            # This is not an error - just return success (idempotent operation)
            logger.info(
                "User not in game (already left or never joined)",
                user_id=user_id,
                game_id=game_id,
            )
            return LeaveMatchmakingResponse(
                message="User was not in the game",
                was_in_game=False,
                game_ended=False,
            )

        # Mark player as left via DAO (idempotent)
        await self.game_dao.set_leave_time(
            db=db,
            game_id=game_id,
            agent_version_id=user_player.agent_version_id,
        )

        logger.info(
            "Player marked as left",
            game_id=str(game_id),
            leaving_player_id=str(user_player.id),
            leaving_user_id=str(user_id),
            agent_version_id=str(user_player.agent_version_id),
        )

        # Use environment hook to emit PlayerLeftEvent and determine finish decision
        registry = GameEnvRegistry.instance()
        env_class = registry.get(game.game_type)

        # Parse config and create environment
        config_dict = game.config or {}
        config_type = env_class.types().config_type()
        config = config_type.model_validate(config_dict)
        env = registry.create(game.game_type, config, analysis_handler=self.analysis_handler)

        # Parse current state
        state_type = env_class.types().state_type()
        parsed_state = state_type.model_validate(game.state or {})

        # Call environment hook to handle player leaving
        event_collector = EventCollector[BaseGameEvent]()
        finish_decision = env.on_player_left(parsed_state, user_player.id, event_collector)

        # Add events to database
        await self.game_dao.add_events(db, game_id, event_collector.get_events())

        # Update player count in database and apply to in-memory instance
        updated_player_count = await self.game_dao.update_player_count(db=db, game_id=game_id)
        game.current_player_count = updated_player_count

        # Bump version so pollers are notified of the leave event
        await self.game_dao.bump_version(db=db, game_id=game_id)
        await db.commit()
        await self._refresh_game_for_response(db=db, game=game)

        # Determine if game should be ended based on environment's decision
        should_end_game = False

        if finish_decision == FinishDecision.CANCEL:
            # No players left - cancel the game
            should_end_game = True
            await self.game_dao.set_status(db=db, game_id=game_id, status=MatchmakingStatus.CANCELLED)
            logger.info(
                "Cancelling game - no players remaining",
                game_id=game_id,
            )
        elif finish_decision == FinishDecision.FINISH:
            # Below minimum players - finish the game with remaining player(s) as winner(s)
            if game.matchmaking_status == MatchmakingStatus.IN_PROGRESS:
                should_end_game = True
                # Refresh game_players to get updated leave_time values
                await db.refresh(game, attribute_names=["game_players"])
                await self._finish_game_with_remaining_players(db, game, env, parsed_state)
                logger.info(
                    "Finishing in-progress game - player left, below minimum players, remaining player wins",
                    game_id=game_id,
                    game_type=game.game_type,
                    remaining_players=game.current_player_count,
                )
            elif game.matchmaking_status == MatchmakingStatus.WAITING:
                # Game is waiting - cancel it since we're below minimum
                should_end_game = True
                await self.game_dao.set_status(db=db, game_id=game_id, status=MatchmakingStatus.CANCELLED)
                logger.info(
                    "Cancelling waiting game - below minimum players",
                    game_id=game_id,
                    current_players=game.current_player_count,
                )
        elif finish_decision == FinishDecision.CONTINUE:
            # Game continues with remaining players
            # For poker games in progress, try to add system agents if needed
            if game.game_type == GameType.TEXAS_HOLDEM and game.matchmaking_status == MatchmakingStatus.IN_PROGRESS:
                await self._handle_poker_player_replacement(db, game, parsed_state)

            logger.info(
                "Player left but game continues with remaining players",
                game_id=game_id,
                game_type=game.game_type,
                remaining_players=game.current_player_count,
            )

        if should_end_game:
            await db.commit()
            await self._refresh_game_for_response(db=db, game=game)

        logger.info(
            "User left matchmaking",
            user_id=user_id,
            game_id=game_id,
            remaining_players=game.current_player_count,
            game_status=game.matchmaking_status.value,
            game_ended=should_end_game,
        )

        return LeaveMatchmakingResponse(
            message="Successfully left the game",
            was_in_game=True,
            game_ended=should_end_game,
        )

    async def handle_waiting_timeouts(self, db: AsyncSession) -> list[Game]:
        """Handle games that have timed out waiting for players.

        This method:
        1. Finds games past their waiting deadline
        2. Fills remaining slots with system agents
        3. Starts the games

        Args:
            db: Database session

        Returns:
            List of games that were started
        """
        logger.debug("Finding timed out games")
        timed_out_games = await self.game_dao.find_timed_out_games(db=db)

        if timed_out_games:
            logger.info("Found timed out games", count=len(timed_out_games), game_ids=[str(g.id) for g in timed_out_games])
        else:
            logger.debug("No timed out games found")

        started_games: list[Game] = []

        for game in timed_out_games:
            logger.info(
                "Processing timed out game",
                game_id=game.id,
                game_type=game.game_type,
                current_players=game.current_player_count,
                min_players=game.min_players_required,
            )

            # Ensure minimum players; try to fill with admin agents if needed
            min_players = game.min_players_required or 0
            if game.current_player_count < min_players:
                slots_needed = min_players - game.current_player_count

                # Get agent versions already in the game to exclude them
                existing_agent_version_ids = {gp.agent_version_id for gp in game.game_players if gp.leave_time is None}

                # Get admin user from database by known email
                admin_user = await self.user_dao.get_by_email(db, "admin@agentleague.app")
                if not admin_user:
                    logger.error("Admin user not found in database", game_id=game.id)
                    await self.game_dao.set_status(db=db, game_id=game.id, status=MatchmakingStatus.CANCELLED)
                    await db.commit()
                    continue

                # Find admin agents (Krang, Shredder), requesting more than needed to account for exclusions
                all_admin_agents = await self.agent_dao.find_admin_agents_for_matchmaking(
                    db=db,
                    game_type=game.game_type,
                    admin_user_id=admin_user.id,
                    limit=slots_needed + len(existing_agent_version_ids),  # Request extra to account for exclusions
                )

                # Filter out agents already in the game
                admin_agents = [a for a in all_admin_agents if a.id not in existing_agent_version_ids]

                logger.info(
                    "Found admin agents for game",
                    game_id=game.id,
                    game_type=game.game_type,
                    slots_needed=slots_needed,
                    found_count=len(admin_agents),
                    agent_ids=[str(a.id) for a in admin_agents],
                    excluded_count=len(existing_agent_version_ids),
                )

                if len(admin_agents) < slots_needed:
                    # Not enough admin agents available — cancel the game
                    logger.warning(
                        "Not enough admin agents to start game, cancelling",
                        game_id=game.id,
                        needed=slots_needed,
                        available=len(admin_agents),
                    )
                    await self.game_dao.set_status(db=db, game_id=game.id, status=MatchmakingStatus.CANCELLED)
                    await db.commit()
                    continue

                # Add admin agents to fill slots atomically via DAO
                added = 0
                for admin_agent in admin_agents[:slots_needed]:
                    result, _, _ = await self.game_dao.join_game_atomically(
                        db=db,
                        game_id=game.id,
                        agent_version_id=admin_agent.id,
                        user_id=admin_agent.user_id,
                        env=game.game_type,
                        is_system_player=True,  # Mark as system player for game logic
                    )
                    if result == JoinResult.JOINED:
                        added += 1

                # Sync current_player_count from DB and commit
                updated = await self.game_dao.update_player_count(db=db, game_id=game.id)
                game.current_player_count = updated
                await db.commit()

                logger.info(
                    "Added admin agents to game",
                    game_id=game.id,
                    admin_agents_added=added,
                    current_players=game.current_player_count,
                    min_players=min_players,
                )

                # If still below minimum after attempted fills, cancel
                if game.current_player_count < min_players:
                    await self.game_dao.set_status(db=db, game_id=game.id, status=MatchmakingStatus.CANCELLED)
                    await db.commit()
                    continue

            # Only start if we now meet or exceed minimum players
            if game.current_player_count >= (game.min_players_required or 0):
                # Refresh to ensure we have the latest values before attempting start
                await db.refresh(
                    game,
                    attribute_names=[
                        "matchmaking_status",
                        "current_player_count",
                        "min_players_required",
                    ],
                )
                logger.info(
                    "Post-fill status",
                    game_id=game.id,
                    current_players=game.current_player_count,
                    min_players=game.min_players_required,
                    status=str(game.matchmaking_status),
                )
                try:
                    logger.info("Attempting to start game after timeout fill", game_id=game.id)
                    await self.sqs_game_turn_handler.start_existing_game(db=db, game_id=game.id)
                    logger.info("Start call completed", game_id=game.id)
                    started_games.append(game)
                except Exception:
                    logger.exception("Failed to start game after timeout", game_id=game.id)
                    # Do not cancel here; leave for next worker pass or explicit cleanup
                    continue

        return started_games

    async def _refresh_game_for_response(self, db: AsyncSession, game: Game) -> None:
        """Refresh core game fields to avoid lazy-loading after returning."""
        await db.refresh(
            game,
            attribute_names=[
                "matchmaking_status",
                "current_player_count",
                "waiting_deadline",
                "allows_midgame_joining",
                "started_at",
                "min_players_required",
                "max_players_allowed",
            ],
        )

    async def _handle_poker_player_replacement(self, db: AsyncSession, game: Game, state: BaseGameState) -> None:
        """Handle replacing a leaving player with a system agent in poker games.

        For poker, when a player leaves, we try to add a system agent to keep the game going.
        The game only ends if all remaining players are system agents.

        Args:
            db: Database session
            game: Game to handle replacement for
            state: Current game state
        """
        # Check if all remaining players are system agents
        remaining_players = [gp for gp in game.game_players if gp.leave_time is None]
        all_system_players = all(gp.is_system_player for gp in remaining_players)

        if all_system_players:
            # All remaining players are system agents - finish the game
            logger.info(
                "All remaining players are system agents, finishing poker game",
                game_id=game.id,
            )
            await self.game_dao.set_status(db=db, game_id=game.id, status=MatchmakingStatus.FINISHED)
            await self.game_dao.set_leave_time_for_game(db, game.id)
            await db.commit()
            return

        # Try to add a system agent to replace the leaving player
        # Get admin user
        admin_user = await self.user_dao.get_by_email(db, "admin@agentleague.app")
        if not admin_user:
            logger.warning("Admin user not found, cannot add system agent to poker game", game_id=game.id)
            return

        # Get agent versions already in the game to exclude them
        existing_agent_version_ids = {gp.agent_version_id for gp in game.game_players if gp.leave_time is None}

        # Find available system agents for poker (Krang, Benedict)
        available_system_agents = await self.agent_dao.find_admin_agents_for_matchmaking(
            db=db,
            game_type=GameType.TEXAS_HOLDEM,
            admin_user_id=admin_user.id,
            limit=len(existing_agent_version_ids) + 2,  # Request extra to account for exclusions
        )

        # Filter out agents already in the game
        available_agents = [a for a in available_system_agents if a.id not in existing_agent_version_ids]

        if not available_agents:
            logger.warning(
                "No available system agents to add to poker game",
                game_id=game.id,
                existing_agents=len(existing_agent_version_ids),
            )
            return

        # Add one system agent
        system_agent = available_agents[0]
        result, _, _ = await self.game_dao.join_game_atomically(
            db=db,
            game_id=game.id,
            agent_version_id=system_agent.id,
            user_id=admin_user.id,
            env=GameType.TEXAS_HOLDEM,
            is_system_player=True,
        )

        if result == JoinResult.JOINED:
            # Update player count
            updated_count = await self.game_dao.update_player_count(db=db, game_id=game.id)
            game.current_player_count = updated_count
            await db.commit()

            logger.info(
                "Added system agent to poker game to replace leaving player",
                game_id=game.id,
                system_agent_version_id=system_agent.id,
                agent_id=system_agent.agent_id,
                current_players=game.current_player_count,
            )
        else:
            logger.warning(
                "Failed to add system agent to poker game",
                game_id=game.id,
                result=result.value,
            )

    async def _finish_game_with_remaining_players(self, db: AsyncSession, game: Game, env: GenericGameEnv, state: BaseGameState) -> None:
        """Finish a game by declaring remaining players as winners.

        This is called when a player leaves and the game falls below minimum players.
        The remaining player(s) win by forfeit.

        Args:
            db: Database session
            game: Game to finish
            env: Game environment instance
            state: Current game state (already parsed)
        """
        # Get remaining active players
        remaining_players = [gp for gp in game.game_players if gp.leave_time is None]

        # Build detailed player info for logging
        all_players_info: list[PlayerInfoForLogging] = []
        for gp in game.game_players:
            username = gp.user.username if gp.user else "unknown"
            agent_name = gp.agent_version.agent.name if gp.agent_version and gp.agent_version.agent else "unknown"
            all_players_info.append(
                PlayerInfoForLogging(
                    player_id=str(gp.id),
                    username=username,
                    agent_name=agent_name,
                    leave_time=str(gp.leave_time) if gp.leave_time else None,
                )
            )

        remaining_players_info: list[RemainingPlayerInfoForLogging] = []
        for gp in remaining_players:
            username = gp.user.username if gp.user else "unknown"
            agent_name = gp.agent_version.agent.name if gp.agent_version and gp.agent_version.agent else "unknown"
            remaining_players_info.append(
                RemainingPlayerInfoForLogging(
                    player_id=str(gp.id),
                    username=username,
                    agent_name=agent_name,
                )
            )

        logger.info(
            "Finishing game with remaining players",
            game_id=str(game.id),
            all_players=[p.model_dump() for p in all_players_info],
            remaining_players=[p.model_dump() for p in remaining_players_info],
        )

        if not remaining_players:
            # No players left - just cancel
            await self.game_dao.set_status(db=db, game_id=game.id, status=MatchmakingStatus.CANCELLED)
            await db.commit()
            return

        # Use environment hook to finish the game
        event_collector = EventCollector[BaseGameEvent]()
        remaining_player_ids = [gp.id for gp in remaining_players]

        logger.info(
            "Calling finish_due_to_forfeit",
            game_id=str(game.id),
            remaining_player_ids=[str(pid) for pid in remaining_player_ids],
        )

        env.finish_due_to_forfeit(state, remaining_player_ids, event_collector)

        # Add any events generated by the hook
        await self.game_dao.add_events(db, game.id, event_collector.get_events())

        # Convert state back to dict for storage
        game.state = state.model_dump(mode="python")
        await self.game_dao.update_game(db, game)
        await self.game_dao.set_status(db, game.id, MatchmakingStatus.FINISHED)

        # Update agent ratings for forfeit game
        await self.game_manager.update_ratings_for_finished_game(db, game, state, type(env))

        # Set leave_time for all remaining players
        await self.game_dao.set_leave_time_for_game(db, game.id)

        await db.commit()

        logger.info(
            "Game finished with remaining players as winners",
            game_id=game.id,
            game_type=game.game_type,
            winner_count=len(remaining_players),
        )

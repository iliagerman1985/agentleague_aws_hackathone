"""SQS handler for game move analysis processing."""

from __future__ import annotations

from typing import Protocol

from game_api import BaseGameEvent, BaseGameState, GameType
from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.sqs_game_messages import GameAnalysisMessage, GameAnalysisSqsClient
from app.services.game_env_registry import GameEnvRegistry
from common.core.request_context import RequestContext
from common.ids import GameId, PlayerId
from common.utils.utils import get_logger
from shared_db.crud.game import GameDAO
from shared_db.db import AsyncSessionLocal

logger = get_logger(__name__)


class AnalysisServiceProtocol(Protocol):
    """Protocol for game-specific analysis services."""

    async def analyze_move(
        self,
        db: AsyncSession,
        game_id: GameId,
        round_number: int,
        player_id: PlayerId,
        move_san: str,
        state_before: BaseGameState,
        state_after: BaseGameState,
    ) -> None:
        """Analyze a move for a specific game type."""
        ...


class SqsGameAnalysisHandler:
    """Handles SQS game analysis messages for different game types.

    This handler processes move analysis requests from the SQS queue,
    checks for existing analysis to prevent duplicates, and delegates
    to registered game-specific analysis services.
    """

    _sqs_client: GameAnalysisSqsClient
    _game_dao: GameDAO
    _analysis_services: dict[GameType, AnalysisServiceProtocol]

    def __init__(
        self,
        sqs_client: GameAnalysisSqsClient,
        game_dao: GameDAO,
    ) -> None:
        self._sqs_client = sqs_client
        self._game_dao = game_dao
        self._analysis_services = {}

        # Register the handler with the SQS client
        self._sqs_client.register_poll_handler(self._handle_game_analysis)

    def register_analysis_service(self, game_type: GameType, service: AnalysisServiceProtocol) -> None:
        """Register an analysis service for a specific game type."""
        self._analysis_services[game_type] = service

    async def _handle_game_analysis(self, message: GameAnalysisMessage, request_context: RequestContext) -> None:
        """Handle a game analysis message from SQS.

        Args:
            message: The analysis message containing game state and move info
            request_context: The request context for logging and tracing
        """
        async with AsyncSessionLocal() as db:
            try:
                logger.info(f"Processing game analysis for game {message.game_id}, round {message.round_number}, move {message.move_san}")

                # Check if analysis already exists (deduplication)
                if await self._check_existing_analysis(
                    db=db,
                    game_id=message.game_id,
                    round_number=message.round_number,
                ):
                    logger.debug(f"Analysis already exists for game {message.game_id}, round {message.round_number}. Skipping.")
                    return

                # Handle analysis generically using the environment's state type
                await self._handle_analysis(db=db, message=message)

                # Commit the transaction (analysis service adds events but doesn't commit)
                await db.commit()
                logger.info(f"Game analysis completed for game {message.game_id}, round {message.round_number}")

            except Exception:
                await db.rollback()
                logger.exception(f"Error processing game analysis for game {message.game_id}, round {message.round_number}")
                raise

    async def _check_existing_analysis(
        self,
        db: AsyncSession,
        game_id: GameId,
        round_number: int,
    ) -> bool:
        """Check if analysis already exists for this game and round.

        Args:
            db: Database session
            game_id: The game ID
            round_number: The round number

        Returns:
            True if analysis exists, False otherwise
        """
        # Get the game type and events using DAO methods
        game_type = await self._game_dao.get_game_type(db=db, game_id=game_id)
        if not game_type:
            logger.warning(f"Game {game_id} not found")
            return False

        events = await self._game_dao.get_events(db=db, game_id=game_id)

        # Check if any event for this round is a Move Analysis event using typed parsing
        registry = GameEnvRegistry.instance()
        env_cls = registry.get(game_type)
        event_union = env_cls.types().event_type()
        adapter = TypeAdapter(event_union)

        def _is_analysis_for_round(ev: BaseGameEvent, target_round: int) -> bool:
            return env_cls.types().is_analysis_event(ev) and ev.turn == target_round

        return any(_is_analysis_for_round(adapter.validate_python(e.data or {}), round_number) for e in events)

    async def _handle_analysis(
        self,
        db: AsyncSession,
        message: GameAnalysisMessage,
    ) -> None:
        """Handle game analysis generically for any game type.

        Args:
            db: Database session
            message: The analysis message with game state data
        """
        # Check if an analysis service is registered for this game type
        service = self._analysis_services.get(message.game_type)
        if not service:
            logger.info(f"No analysis service registered for game type {message.game_type}")
            return

        # Parse the state data using the environment's state type
        registry = GameEnvRegistry.instance()
        env_cls = registry.get(message.game_type)
        state_type = env_cls.types().state_type()

        state_before = state_type.model_validate(message.state_before_data)
        state_after = state_type.model_validate(message.state_after_data)

        # Delegate to the registered analysis service
        await service.analyze_move(
            db=db,
            game_id=message.game_id,
            round_number=message.round_number,
            player_id=message.player_id,
            move_san=message.move_san,
            state_before=state_before,
            state_after=state_after,
        )

    async def queue_analysis(
        self,
        game_id: GameId,
        game_type: GameType,
        round_number: int,
        player_id: PlayerId,
        move_san: str,
        state_before: BaseGameState,
        state_after: BaseGameState,
    ) -> None:
        """Queue a move analysis request to SQS.

        Args:
            game_id: The game ID
            game_type: The type of game
            round_number: The round number
            player_id: The player ID
            move_san: The move in standard notation
            state_before: Game state before the move
            state_after: Game state after the move
        """
        message = GameAnalysisMessage(
            game_id=game_id,
            game_type=game_type,
            round_number=round_number,
            player_id=player_id,
            move_san=move_san,
            state_before_data=state_before.model_dump(),
            state_after_data=state_after.model_dump(),
        )

        await self._sqs_client.send(message)
        logger.info(f"Queued analysis for game {game_id}, round {round_number}, move {move_san}")

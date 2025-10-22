from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.sqs_game_messages import GameTurnMessage, GameTurnSqsClient
from app.services.game_manager import GameManager
from common.core.app_error import Errors
from common.core.request_context import RequestContext
from common.ids import GameId, PlayerId
from common.utils.utils import get_logger
from shared_db.db import AsyncSessionLocal

logger = get_logger()


class SqsGameTurnHandler:
    """Handles SQS game turn messages, breaking the circular dependency between GameManager and SQS client.

    This class registers a handler on the SQS client that calls GameManager to process turns,
    and then sends the next turn message back to SQS if the game is still in progress.
    """

    _sqs_client: GameTurnSqsClient
    _game_manager: GameManager

    def __init__(
        self,
        sqs_client: GameTurnSqsClient,
        game_manager: GameManager,
    ) -> None:
        self._sqs_client = sqs_client
        self._game_manager = game_manager

        self._sqs_client.register_poll_handler(self._handle_game_turn)

    async def _handle_game_turn(self, message: GameTurnMessage, request_context: RequestContext) -> None:
        # Get database session
        async with AsyncSessionLocal() as db:
            try:
                # Process the turn through GameManager
                logger.info(f"Processing game turn for game {message.game_id}, player {message.player_id}, turn {message.turn}")

                state, _ = await self._game_manager.process_turn(
                    db=db,
                    request_id=request_context.request_id,
                    game_id=message.game_id,
                    player_id=message.player_id,
                    turn=message.turn,
                    move_override=None,
                    is_playground=False,
                )
                await db.commit()

                # Send next turn message if the game is not finished
                if not state.is_finished:
                    await self._send_next_turn_message(
                        game_id=message.game_id,
                        next_player_id=state.current_player_id,
                        turn=state.turn,
                    )

                logger.info(f"Game turn processed successfully for game {message.game_id}")

            except Exception as e:
                await db.rollback()

                # Check if this is a turn advancement conflict
                if Errors.Game.TURN_ADVANCEMENT_CONFLICT.is_(e):
                    # This is expected when another handler processed the turn
                    # Log and let the message be deleted (non-retryable)
                    logger.info(f"Turn advancement conflict for game {message.game_id}, turn {message.turn}. Another handler processed this turn.")
                    return

                # Re-raise for SQS client to handle retry logic
                logger.exception(f"Error processing game turn for game {message.game_id}")
                raise
            finally:
                await db.close()

    async def _send_next_turn_message(
        self,
        game_id: GameId,
        next_player_id: PlayerId,
        turn: int,
    ) -> None:
        """Send the next turn message to SQS.

        Args:
            game_id: The game ID
            next_player_id: The next player ID
            turn: The next turn number
        """
        message = GameTurnMessage(
            game_id=game_id,
            player_id=next_player_id,
            turn=turn,
        )
        await self._sqs_client.send(message)
        logger.info(f"Sent next turn message for game {game_id}, player {next_player_id}, turn {turn}")

    async def start_existing_game(self, db: AsyncSession, game_id: GameId) -> None:
        """Start an existing game by calling GameManager and sending initial turn message to SQS.

        Args:
            db: Database session
            game_id: The game ID
        """

        # Call GameManager to start the game
        state, _ = await self._game_manager.start_existing_game(db, game_id)

        # Send initial turn message to SQS if the game is not finished
        if not state.is_finished:
            message = GameTurnMessage(
                game_id=game_id,
                player_id=state.current_player_id,
                turn=state.turn,
            )
            await self._sqs_client.send(message)
            logger.info(f"Sent initial turn message for game {game_id}, player {state.current_player_id}, turn {state.turn}")

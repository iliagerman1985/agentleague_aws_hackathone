"""Background worker for matchmaking timeout processing."""

import asyncio
from contextlib import suppress
from datetime import UTC, datetime, timedelta

from app.service_container import Services
from common.core.request_context import RequestContext
from common.utils.utils import get_logger
from shared_db.db import AsyncSessionLocal

logger = get_logger()


class MatchmakingWorker:
    """Background worker that processes matchmaking timeouts."""

    def __init__(self, check_interval_seconds: int = 1) -> None:
        """Initialize the matchmaking worker.

        Args:
            check_interval_seconds: How often to check for timed out games
        """
        self.check_interval_seconds = check_interval_seconds
        self.task: asyncio.Task[None] | None = None
        self.running = False

    async def start(self) -> None:
        """Start the background worker."""
        if self.running:
            logger.warning("Matchmaking worker already running")
            return

        self.running = True
        self.task = asyncio.create_task(self._run())
        logger.info("Matchmaking worker started", check_interval=self.check_interval_seconds)

    async def stop(self) -> None:
        """Stop the background worker."""
        if not self.running:
            return

        self.running = False
        if self.task:
            _ = self.task.cancel()
            with suppress(asyncio.CancelledError):
                await self.task
            self.task = None

        logger.info("Matchmaking worker stopped")

    async def _run(self) -> None:
        """Main worker loop."""
        logger.info("Matchmaking worker main loop started")
        while self.running:
            with RequestContext.context():
                try:
                    logger.debug("Matchmaking worker checking for timeouts")
                    await self._process_timeouts()
                    await self._cleanup_old_games()
                except Exception as e:
                    logger.exception("Error in matchmaking worker", exc_info=e)

            # Wait before next check
            await asyncio.sleep(self.check_interval_seconds)

    async def _process_timeouts(self) -> None:
        """Process timed out games."""
        async with AsyncSessionLocal() as db:
            try:
                services = Services.instance()

                logger.debug("Calling handle_waiting_timeouts")
                started_games = await services.game_matching_service.handle_waiting_timeouts(db)

                if started_games:
                    logger.info(
                        "Processed matchmaking timeouts",
                        games_started=len(started_games),
                        game_ids=[str(g.id) for g in started_games],
                    )
                else:
                    logger.debug("No timed out games found")

                await db.commit()
            except Exception:
                logger.exception("Error processing matchmaking timeouts")
                await db.rollback()
                raise
            finally:
                await db.close()

    async def _cleanup_old_games(self) -> None:
        """Clean up old WAITING games that are stuck (older than 10 minutes)."""
        async with AsyncSessionLocal() as db:
            try:
                game_dao = Services.instance().game_dao

                cutoff_time = datetime.now(UTC) - timedelta(minutes=10)

                old_games = await game_dao.find_old_waiting_games(db, cutoff_time)
                if old_games:
                    cancelled = await game_dao.cancel_old_waiting_games(db, cutoff_time)
                    await db.commit()

                    logger.info(
                        "Cancelled old waiting games",
                        games_cancelled=cancelled,
                        game_ids=[str(g.id) for g in old_games],
                    )
                await db.commit()
            except Exception:
                logger.exception("Error cleaning up old games")
                await db.rollback()
            finally:
                await db.close()


class MatchmakingWorkerManager:
    """Manager for the matchmaking worker singleton."""

    def __init__(self) -> None:
        """Initialize the worker manager."""
        self._worker: MatchmakingWorker | None = None

    async def start(self) -> None:
        """Start the matchmaking worker."""
        if self._worker is None:
            self._worker = MatchmakingWorker()
        await self._worker.start()

    async def stop(self) -> None:
        """Stop the matchmaking worker."""
        if self._worker:
            await self._worker.stop()


# Singleton instance
_manager = MatchmakingWorkerManager()


async def start_matchmaking_worker() -> None:
    """Start the global matchmaking worker."""
    await _manager.start()


async def stop_matchmaking_worker() -> None:
    """Stop the global matchmaking worker."""
    await _manager.stop()

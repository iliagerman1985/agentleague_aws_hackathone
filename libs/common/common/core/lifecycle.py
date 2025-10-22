import atexit
from abc import ABC, abstractmethod

from common.utils.utils import blocking_run_async, get_logger

logger = get_logger()


class Lifecycle(ABC):
    _is_running: bool

    def __init__(self) -> None:
        self._is_running = False

    async def start(self) -> None:
        if self._is_running:
            return
        self._is_running = True
        atexit.register(self._stop_sync)

        try:
            logger.info(f"{self._name_for_log}: Starting...")
            await self._start()
            logger.info(f"{self._name_for_log} Started.")
        except Exception as e:
            logger.exception(f"{self._name_for_log}: Failed to start!", exc_info=e)
            await self.stop()
            raise e

    @abstractmethod
    async def _start(self) -> None:
        pass

    async def stop(self) -> None:
        if not self._is_running:
            return
        self._is_running = False

        try:
            logger.info(f"{self._name_for_log}: Stopping...")
            await self._stop()
            logger.info(f"{self._name_for_log}: Stopped.")
        except Exception as e:
            self._is_running = True
            logger.exception(f"{self._name_for_log}: Failed to stop!", exc_info=e)
            raise e

    @abstractmethod
    async def _stop(self) -> None:
        pass

    def _stop_sync(self) -> None:
        blocking_run_async(self.stop())

    @property
    def _name_for_log(self) -> str:
        return self.__class__.__name__

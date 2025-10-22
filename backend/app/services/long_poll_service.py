"""Reusable long-polling helper.

Provides a small utility to wait until a version-like value changes,
with optional client-cancellation support.
"""

import asyncio
from collections.abc import Awaitable, Callable

from common.utils.utils import get_now


class LongPollService:
    async def wait_for_change(
        self,
        initial_value: int | None,
        get_current_value: Callable[[], Awaitable[int | None]],
        *,
        timeout_s: int = 30,
        interval_s: float = 0.2,
        cancel_check: Callable[[], Awaitable[bool]] | None = None,
    ) -> bool:
        """Wait until the value returned by get_current_value differs from initial_value.

        Args:
            initial_value: The reference value to compare against.
            get_current_value: Async function returning the current value.
            timeout_s: Maximum time to wait in seconds (1..60).
            interval_s: Sleep interval between checks.
            cancel_check: Optional async predicate that returns True if the client
                disconnected or the operation should be cancelled.

        Returns:
            True if the value changed before timeout, False on timeout.

        Raises:
            asyncio.CancelledError: If cancel_check returns True.
        """
        timeout_s = max(1, min(timeout_s, 60))
        start = get_now()

        while (get_now() - start).total_seconds() < float(timeout_s):
            if cancel_check and await cancel_check():
                raise asyncio.CancelledError()

            current = await get_current_value()
            if current != initial_value:
                return True

            await asyncio.sleep(interval_s)

        return False

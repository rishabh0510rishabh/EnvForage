"""In-flight SSE stream tracking for graceful shutdown.

Active streaming responses register themselves with a :class:`StreamTracker`
stored on ``app.state`` so the application lifespan can wait for them to finish
before the process exits — e.g. on a SIGTERM during a Kubernetes rolling
update — instead of abruptly severing live LLM streams.
"""

import asyncio
import logging
from collections.abc import AsyncIterator

logger = logging.getLogger(__name__)


class StreamTracker:
    """Count in-flight streaming responses and wait for them to drain."""

    def __init__(self) -> None:
        self._active = 0
        self._idle = asyncio.Event()
        self._idle.set()

    @property
    def active(self) -> int:
        """Number of streams currently in flight."""
        return self._active

    def track(self, stream: AsyncIterator[str]) -> AsyncIterator[str]:
        """Wrap *stream*, counting it as active until it is exhausted or closed."""
        self._active += 1
        self._idle.clear()
        return self._guard(stream)

    async def _guard(self, stream: AsyncIterator[str]) -> AsyncIterator[str]:
        try:
            async for item in stream:
                yield item
        finally:
            self._active -= 1
            if self._active <= 0:
                self._active = 0
                self._idle.set()

    async def drain(self, timeout: float) -> bool:
        """Wait until all active streams finish or *timeout* seconds elapse.

        Returns ``True`` if every stream drained, ``False`` if the timeout was
        reached while streams were still active.
        """
        if self._active == 0:
            return True
        logger.info(
            "Waiting up to %.1fs for %d active stream(s) to finish",
            timeout,
            self._active,
        )
        try:
            await asyncio.wait_for(self._idle.wait(), timeout)
        except TimeoutError:
            logger.warning(
                "Shutdown timeout reached with %d stream(s) still active",
                self._active,
            )
            return False
        return True

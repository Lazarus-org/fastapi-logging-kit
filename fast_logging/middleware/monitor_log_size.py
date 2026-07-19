import logging
from datetime import datetime, timedelta, timezone

import anyio.to_thread
from starlette.types import Receive, Scope, Send

from fast_logging.cache import cache
from fast_logging.middleware.base import BaseMiddleware

logger = logging.getLogger(__name__)

CACHE_KEY = "last_run_logs_size_audit"


class MonitorLogSizeMiddleware(BaseMiddleware):
    """Middleware that monitors the size of the log directory.

    This middleware checks if a week has passed since the last log size audit. If so, it runs
    the 'logs_size_audit' command, which checks the log directory's total size.
    If the size exceeds a configured limit, a warning email is sent to the admin.

    The audit walks the log directory and may send an email, so it runs in
    a worker thread to keep the event loop responsive.

    Attributes:
    ----------
        app (ASGIApp): The next application in the middleware stack.

    """

    async def dispatch(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Runs the audit when due, then processes the request.

        Args:
        ----
            scope (Scope): The ASGI connection scope.
            receive (Receive): The ASGI receive channel.
            send (Send): The ASGI send channel.

        """
        if await anyio.to_thread.run_sync(self.should_run_task):
            await anyio.to_thread.run_sync(self.run_log_size_check)
            cache.set(CACHE_KEY, self._now(), timeout=None)

        await self.app(scope, receive, send)

    @staticmethod
    def _now() -> datetime:
        """Return the current time as an aware UTC datetime.

        Returns:
            datetime: The current UTC time.

        """
        return datetime.now(timezone.utc)

    @classmethod
    def should_run_task(cls) -> bool:
        """Determines if a week has passed since the last log size audit.

        Returns:
        -------
            bool: True if a week has passed since the last audit, False otherwise.

        """
        last_run = cache.get(CACHE_KEY)
        if last_run is None or cls._now() - last_run > timedelta(weeks=1):
            return True

        return False

    def run_log_size_check(self) -> None:
        """Runs the 'logs_size_audit' command to check the log directory size.

        If an error occurs during the execution of the command, it is
        logged.

        """
        from fast_logging.commands.logs_size_audit import run as run_logs_size_audit

        logger.info("Running 'logs_size_audit' command...")
        try:
            run_logs_size_audit()
        except Exception as e:  # pylint: disable=W0718
            logger.error("Error running 'logs_size_audit' command: %s", e)

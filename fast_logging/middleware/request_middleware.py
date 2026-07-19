import asyncio
import logging
from time import perf_counter
from typing import Dict, List, Optional
from uuid import uuid4

from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from fast_logging.contextvar import manager
from fast_logging.middleware.base import BaseMiddleware, get_header
from fast_logging.utils.get_conf import is_log_sql_queries_enabled
from fast_logging.utils.request import (
    get_ip_address,
    get_request_id,
    get_user,
    get_user_agent,
)
from fast_logging.utils.sql import clear_queries, get_queries
from fast_logging.utils.time import format_elapsed_time

logger = logging.getLogger(__name__)


class RequestLogMiddleware(BaseMiddleware):
    """Middleware to log information about each incoming request.

    Every request is assigned a request ID, which — together with the
    client IP and user agent — is bound to the context variables so that
    every log record emitted while handling the request carries it.

    Streaming responses are logged separately: a "Streaming started"
    record is emitted when the first body chunk is sent and a
    "Streaming finished" record once the response completes.

    Attributes:
        app (ASGIApp): The next application in the middleware stack.
        log_sql (bool): Whether SQL queries should be reported per request.

    """

    def __init__(self, app: ASGIApp) -> None:
        """Initializes the RequestLogMiddleware instance.

        Args:
            app (ASGIApp): The next ASGI application to call.

        """
        super().__init__(app)
        self.log_sql = is_log_sql_queries_enabled()

    async def dispatch(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handles the request, logging its start and completion.

        Args:
            scope (Scope): The ASGI connection scope.
            receive (Receive): The ASGI receive channel.
            send (Send): The ASGI send channel.

        Raises:
            asyncio.CancelledError: Re-raised after logging, when the
                client disconnects before the response completes.

        """
        request = Request(scope, receive=receive)
        request_id = self._prepare_request(request)
        start_time = perf_counter()

        if self.log_sql:
            clear_queries()

        state: Dict[str, object] = {
            "status_code": 0,
            "content_type": "Unknown",
            "chunks": 0,
            "finalized": False,
        }

        async def send_wrapper(message: Message) -> None:
            """Capture response metadata on the way out."""
            if message["type"] == "http.response.start":
                state["status_code"] = message["status"]
                state["content_type"] = get_header(message, "content-type")

            elif message["type"] == "http.response.body":
                chunks = int(state["chunks"]) + 1
                state["chunks"] = chunks

                # A second body message means the response is streaming.
                if chunks == 2:
                    logger.info("Streaming started: request_id=%s", request_id)

                if not message.get("more_body", False):
                    if chunks > 1:
                        logger.info("Streaming finished: request_id=%s", request_id)
                    self._finalize_request(request, state, start_time)

            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except asyncio.CancelledError:
            logger.warning("Request was cancelled: request_id=%s", request_id)
            manager.clear()
            raise
        except Exception:
            if state["chunks"]:
                logger.exception("Streaming failed: request_id=%s", request_id)
            self._finalize_request(request, state, start_time)
            raise

        # An application that never sent a final body message still gets
        # finalized, so the context variables are always released.
        self._finalize_request(request, state, start_time)

    def _prepare_request(self, request: Request) -> str:
        """Prepares the request for processing by generating a request ID and
        logging initial details.

        Args:
            request (Request): The incoming request.

        Returns:
            str: The generated or retrieved request ID.

        """
        request_id = get_request_id(request) or str(uuid4())

        ip_address = get_ip_address(request)
        user_agent = get_user_agent(request)

        self.context = {  # pylint: disable=W0201
            "request_id": request_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
        }

        manager.bind(**self.context)

        log_message = (
            f"REQUEST STARTED:\n\tmethod={request.method}\n\t"
            f"path={request.url.path}\n\t"
            f"query_params={dict(request.query_params) or None}\n\t"
            f"referrer={request.headers.get('referer', 'None')}\n"
        )
        logger.info(log_message)

        return request_id

    def _finalize_request(
        self,
        request: Request,
        state: Dict[str, object],
        start_time: float,
    ) -> None:
        """Finalizes the request by logging the response details and the time
        taken to process the request.

        Args:
            request (Request): The incoming request.
            state (Dict[str, object]): The captured response metadata.
            start_time (float): The time when the request started.

        """
        if state["finalized"]:
            return
        state["finalized"] = True

        user = get_user(request)
        status_code = state["status_code"]
        content_type = state["content_type"]
        response_time = format_elapsed_time(perf_counter() - start_time)

        sql_log = self._log_sql_queries() if self.log_sql else ""

        logger.info(
            "REQUEST FINISHED:\n\tuser=%s\n\tstatus_code=%d"
            "\n\tcontent_type=[%s]\n\tresponse_time=[%s]\n\t%s",
            user,
            status_code,
            content_type,
            response_time,
            sql_log,
        )
        manager.clear()

    @staticmethod
    def _log_sql_queries(test_queries: Optional[List[Dict]] = None) -> Optional[str]:
        """Formats the SQL queries executed during the request.

        Args:
            test_queries (Optional[List[Dict]]): A list of test queries to simulate the real query logs.
                This is used for testing purposes to avoid interacting with a real database.
                Each query in the list should contain 'time' and 'sql' keys.

        Returns:
            Optional[str]: The formatted string of SQL queries or None if no queries were executed.

        Queries are read from the per-context log in ``fast_logging.utils.sql``,
        which ``instrument_sqlalchemy`` fills in. Applications using another
        database library can call ``record_query`` from their own instrumentation.

        Example of test_queries format:
            test_queries = [{'time': '0.02', 'sql': 'SELECT * FROM table_name'}]

        """
        # Use test queries if provided, otherwise read the recorded queries.
        new_queries = test_queries or get_queries()

        if not new_queries:
            return None

        # Build the query messages in a single pass.
        query_messages = [
            f"\t\tQuery{idx}={{'Time': {query['time']}(s), 'Query': [{query['sql']}]}}\n\t"
            for idx, query in enumerate(new_queries, start=1)
        ]

        # Return the final formatted message.
        return (
            f"{len(new_queries)} SQL QUERIES EXECUTED\n"
            + "\n".join(query_messages)
            + "\n"
        )

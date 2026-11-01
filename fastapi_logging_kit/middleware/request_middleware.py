import asyncio
import ipaddress
import json
import logging
from contextlib import nullcontext
from time import perf_counter
from typing import Any, Dict, List, Mapping, Optional, TypedDict, cast
from urllib.parse import parse_qsl
from uuid import uuid4

from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from fastapi_logging_kit.contextvar import manager
from fastapi_logging_kit.middleware.base import BaseMiddleware, get_header
from fastapi_logging_kit.middleware.diagnostics import (
    format_json_diagnostic,
    is_json_content_type,
    is_sensitive_field,
    safe_path,
    sanitize_user_agent,
)
from fastapi_logging_kit.utils.get_conf import is_log_sql_queries_enabled
from fastapi_logging_kit.utils.request import (
    get_ip_address,
    get_request_id,
    get_user,
    get_user_agent,
)
from fastapi_logging_kit.utils.sql import (
    get_queries,
    query_capture,
    query_capture_truncated,
)
from fastapi_logging_kit.utils.time import format_elapsed_time

logger = logging.getLogger(__name__)


class _RequestState(TypedDict):
    status_code: int
    content_type: str
    chunks: int
    streaming: bool
    finalized: bool
    cancelled: bool
    request_body: bytearray
    request_body_oversized: bool
    request_body_complete: bool
    error_body: bytearray
    error_body_oversized: bool


class RequestLogMiddleware(BaseMiddleware):
    """Middleware to log information about each incoming request.

    Every request is assigned a request ID, which — together with the
    client IP and user agent — is bound to the context variables so that
    a handler using ContextVarFilter can include it in log output.

    Context remains active until the final response chunk. Additional streaming
    lifecycle records are opt-in for structured configuration and enabled by
    default for direct legacy middleware.

    Attributes:
        app (ASGIApp): The next application in the middleware stack.
        log_sql (bool): Whether SQL queries should be reported per request.
    """

    # pylint: disable=too-many-instance-attributes

    def __init__(
        self,
        app: ASGIApp,
        config: Optional[Mapping[str, Any]] = None,
    ) -> None:
        """Initializes the RequestLogMiddleware instance.

        Args:
            app (ASGIApp): The next ASGI application to call.
        """
        super().__init__(app)
        if config is None:
            self.configuration = None
            request_config: Mapping[str, Any] = {}
        else:
            # Normalize direct middleware usage as well as setup_logging() usage;
            # callers may supply only the options they want to override.
            from fastapi_logging_kit.settings.contract import compile_settings

            self.configuration = compile_settings({"REQUEST_LOGGING": config})[
                "REQUEST_LOGGING"
            ]
            request_config = self.configuration

        self.log_sql = (
            is_log_sql_queries_enabled()
            if config is None
            else bool(request_config["LOG_SQL_QUERIES"])
        )
        self.max_sql_bytes = 4096 if config is None else request_config["MAX_SQL_BYTES"]
        self.max_sql_queries = (
            100 if config is None else request_config["MAX_SQL_QUERIES"]
        )
        self.log_sql = self.log_sql and self.max_sql_bytes > 0
        self.log_streaming_events = (
            True if config is None else request_config["LOG_STREAMING_EVENTS"]
        )
        self.log_started = (
            True if config is None else bool(request_config["LOG_REQUEST_STARTED"])
        )
        self.log_finished = (
            True if config is None else bool(request_config["LOG_REQUEST_FINISHED"])
        )
        self.log_exceptions = (
            True if config is None else bool(request_config["LOG_EXCEPTIONS"])
        )
        self.request_id_header = request_config.get("REQUEST_ID_HEADER", "X-Request-ID")
        self.response_id_header = (
            None if config is None else request_config["RESPONSE_ID_HEADER"]
        )
        self.excluded_paths = frozenset(request_config.get("EXCLUDED_PATHS", ()))
        self.excluded_prefixes = tuple(
            prefix.rstrip("/")
            for prefix in request_config.get("EXCLUDED_PATH_PREFIXES", ())
        )
        self.trusted_proxies = tuple(
            ipaddress.ip_network(proxy, strict=False)
            for proxy in request_config.get("TRUSTED_PROXIES", ())
        )

    async def dispatch(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Log one HTTP request while isolating all state to its ASGI task."""
        # pylint: disable=too-many-statements,too-many-boolean-expressions
        path = scope.get("path", "")
        if path in self.excluded_paths or any(
            path == prefix or path.startswith(prefix + "/")
            for prefix in self.excluded_prefixes
        ):
            await self.app(scope, receive, send)
            return
        request = Request(scope, receive=receive)
        request_id = self._prepare_request(request)
        start_time = perf_counter()
        context = {
            "request_id": request_id,
            "ip_address": self._client_ip(request),
            **(
                {"user_agent": sanitize_user_agent(get_user_agent(request))}
                if self.configuration is None
                or self.configuration["USER_AGENT_ENABLED"]
                else {}
            ),
        }

        state: _RequestState = {
            "status_code": 0,
            "content_type": "Unknown",
            "chunks": 0,
            "streaming": False,
            "finalized": False,
            "cancelled": False,
            "request_body": bytearray(),
            "request_body_oversized": False,
            "request_body_complete": False,
            "error_body": bytearray(),
            "error_body_oversized": False,
        }

        async def receive_wrapper() -> Message:
            """Observe request chunks without consuming or changing them."""
            message = await receive()
            if (
                self.configuration is not None
                and self.configuration["REQUEST_BODY_ENABLED"]
                and self.log_finished
                and logger.isEnabledFor(logging.INFO)
                and request.method in ("POST", "PUT", "PATCH")
                and message["type"] == "http.request"
                and is_json_content_type(request.headers.get("content-type", ""))
            ):
                body = message.get("body", b"")
                if not state["request_body_oversized"] and body:
                    buffer = state["request_body"]
                    limit = self.configuration["MAX_BODY_BYTES"]
                    if len(buffer) + len(body) > limit:
                        buffer.clear()
                        state["request_body_oversized"] = True
                    else:
                        buffer.extend(body)
                if not message.get("more_body", False):
                    state["request_body_complete"] = True
            return message

        async def send_wrapper(message: Message) -> None:
            """Capture bounded error diagnostics while forwarding every message."""
            finalize_after_send = False
            finish_streaming_after_send = False
            if message["type"] == "http.response.start":
                if self.response_id_header:
                    header = self.response_id_header.lower().encode("ascii")
                    message = dict(message)
                    message["headers"] = [
                        (key, value)
                        for key, value in message.get("headers", [])
                        if key.lower() != header
                    ] + [(header, request_id.encode("ascii"))]
                state["status_code"] = message["status"]
                state["content_type"] = get_header(message, "content-type")
            elif message["type"] == "http.response.body":
                chunks = int(state["chunks"]) + 1
                state["chunks"] = chunks
                if (
                    self.configuration is not None
                    and self.configuration["ERROR_RESPONSE_BODY_ENABLED"]
                    and self.log_finished
                    and logger.isEnabledFor(logging.INFO)
                    and int(state["status_code"]) >= 400
                    and is_json_content_type(str(state["content_type"]))
                    and not state["error_body_oversized"]
                ):
                    body = message.get("body", b"")
                    if body:
                        buffer = state["error_body"]
                        limit = self.configuration["MAX_ERROR_RESPONSE_BYTES"]
                        if len(buffer) + len(body) > limit:
                            buffer.clear()
                            state["error_body_oversized"] = True
                        else:
                            buffer.extend(body)
                if message.get("more_body", False) and not state["streaming"]:
                    state["streaming"] = True
                    if self.log_streaming_events:
                        logger.info("Streaming started: request_id=%s", request_id)
                if not message.get("more_body", False):
                    finish_streaming_after_send = bool(
                        state["streaming"] and self.log_streaming_events
                    )
                    finalize_after_send = self.log_finished
            await send(message)
            if finish_streaming_after_send:
                logger.info("Streaming finished: request_id=%s", request_id)
            if finalize_after_send:
                self._finalize_request(request, state, start_time)

        # ContextVar tokens restore any caller context, including on exceptions
        # and cancellation. Never clear the manager globally from middleware.
        capture_scope = (
            query_capture(
                max_bytes=self.max_sql_bytes,
                max_queries=self.max_sql_queries,
            )
            if self.log_sql
            else nullcontext()
        )
        with manager.scoped_context(**context), capture_scope:
            try:
                if self.log_started:
                    logger.info(
                        "REQUEST STARTED: method=%s path=%s request_id=%s",
                        request.method,
                        safe_path(request.url.path),
                        request_id,
                    )
                await self.app(scope, receive_wrapper, send_wrapper)
            except asyncio.CancelledError:
                state["cancelled"] = True
                if self.log_exceptions:
                    logger.warning("Request was cancelled: request_id=%s", request_id)
                raise
            except Exception:
                if self.log_exceptions:
                    if state["streaming"]:
                        logger.exception("Streaming failed: request_id=%s", request_id)
                    else:
                        logger.exception(
                            "REQUEST FAILED: method=%s path=%s request_id=%s",
                            request.method,
                            safe_path(request.url.path),
                            request_id,
                        )
                if self.log_finished:
                    self._finalize_request(request, state, start_time)
                raise
            finally:
                # Covers applications that return without a final body event.
                # A cancelled request is not a completed response.
                if not state["cancelled"] and self.log_finished:
                    self._finalize_request(request, state, start_time)

    def _prepare_request(self, request: Request) -> str:
        """Return a bounded, safe request ID without mutating middleware state."""
        requested_id = (
            get_request_id(request)
            if self.configuration is None
            else request.headers.get(self.request_id_header)
        )
        max_length = (
            80
            if self.configuration is None
            else self.configuration["MAX_REQUEST_ID_LENGTH"]
        )
        valid = (
            isinstance(requested_id, str)
            and requested_id.isascii()
            and 0 < len(requested_id) <= max_length
            and all(char.isalnum() or char in "-_." for char in requested_id)
        )
        request_id = cast(str, requested_id) if valid else str(uuid4())
        request.scope.setdefault("state", {})["request_id"] = request_id
        return request_id

    def _finalize_request(
        self,
        request: Request,
        state: _RequestState,
        start_time: float,
    ) -> None:
        """Finalizes the request by logging the response details and the time taken to
        process the request.

        Args:
            request (Request): The incoming request.
            state (Dict[str, object]): The captured response metadata.
            start_time (float): The time when the request started.
        """
        if state["finalized"]:
            return
        state["finalized"] = True
        if not self.log_finished or not logger.isEnabledFor(logging.INFO):
            return

        user = safe_path(get_user(request), max_length=256)
        status_code = state["status_code"]
        content_type = safe_path(str(state["content_type"]), max_length=128)
        response_time = format_elapsed_time(perf_counter() - start_time)

        sql_log = (
            self._log_sql_queries(
                max_bytes=self.max_sql_bytes,
                truncated=query_capture_truncated(),
            )
            if self.log_sql
            else ""
        ) or ""

        query_diagnostic = self._query_diagnostic(request)
        body_diagnostics = self._body_diagnostics(request, state)
        logger.info(
            "REQUEST FINISHED:\n\tuser=%s\n\tstatus_code=%d"
            "\n\tcontent_type=[%s]\n\tresponse_time=[%s]\n\t%s%s%s",
            user,
            status_code,
            content_type,
            response_time,
            sql_log,
            (
                "\n\tquery_params=" + query_diagnostic
                if query_diagnostic is not None
                else ""
            ),
            body_diagnostics,
        )

    def _body_diagnostics(self, request: Request, state: _RequestState) -> str:
        """Return opt-in, bounded JSON request/error-body diagnostics.

        Only JSON media types are decoded. Unsupported media types and invalid JSON are
        represented by markers; raw bytes are never logged.
        """
        config = self.configuration
        if config is None:
            return ""
        path = request.scope.get("path", "")
        excluded = list(config["EXCLUDED_FIELDS"])
        excluded.extend(config["EXCLUDED_FIELDS_BY_PATH"].get(path, ()))
        depth = config["MAX_DIAGNOSTIC_DEPTH"]
        parts: List[str] = []
        value: Optional[str]

        if config["REQUEST_BODY_ENABLED"] and request.method in (
            "POST",
            "PUT",
            "PATCH",
        ):
            if not is_json_content_type(request.headers.get("content-type", "")):
                value = "<unsupported content type>"
            elif state["request_body_oversized"]:
                value = "<oversized request body>"
            elif not state["request_body_complete"]:
                value = "<incomplete request body>"
            else:
                value = format_json_diagnostic(
                    bytes(state["request_body"]),
                    request.headers.get("content-type", ""),
                    excluded_fields=excluded,
                    max_depth=depth,
                    max_output_bytes=config["MAX_BODY_BYTES"],
                )
            if value is not None:
                parts.append("request_body=" + value)

        if config["ERROR_RESPONSE_BODY_ENABLED"] and int(state["status_code"]) >= 400:
            if state["error_body_oversized"]:
                value = "<oversized error response body>"
            else:
                value = format_json_diagnostic(
                    bytes(state["error_body"]),
                    str(state["content_type"]),
                    excluded_fields=excluded,
                    max_depth=depth,
                    max_output_bytes=config["MAX_ERROR_RESPONSE_BYTES"],
                )
            if value is not None:
                parts.append("error_response_body=" + value)
        return "" if not parts else "\n\t" + "\n\t".join(parts)

    def _query_diagnostic(self, request: Request) -> Optional[str]:
        """Capture opt-in query values with byte bounds and key-based redaction."""
        config = self.configuration
        if config is None or not config["QUERY_PARAMS_ENABLED"]:
            return None
        query = request.scope.get("query_string", b"")
        if not isinstance(query, bytes) or not query:
            return None
        if len(query) > config["MAX_QUERY_BYTES"]:
            return "<oversized query string>"
        path = request.scope.get("path", "")
        exclusions = {
            name.casefold().replace("-", "_").replace(".", "_")
            for name in config["EXCLUDED_FIELDS"]
        }
        exclusions.update(
            name.casefold().replace("-", "_").replace(".", "_")
            for name in config["EXCLUDED_FIELDS_BY_PATH"].get(path, ())
        )
        try:
            pairs = parse_qsl(
                query.decode("utf-8", errors="replace"),
                keep_blank_values=True,
                max_num_fields=128,
            )
            result: Dict[str, Any] = {}
            for key, value in pairs:
                safe = (
                    "[REDACTED]" if is_sensitive_field(key, list(exclusions)) else value
                )
                safe_key = key[:128]
                if safe_key not in result:
                    result[safe_key] = safe
                elif isinstance(result[safe_key], list):
                    result[safe_key].append(safe)
                else:
                    result[safe_key] = [result[safe_key], safe]
            serialized = json.dumps(result, ensure_ascii=True)
            if len(serialized.encode("utf-8")) > config["MAX_QUERY_BYTES"]:
                return "<oversized query string>"
            return serialized
        except (ValueError, UnicodeError):
            return "<unparseable query string>"

    def _client_ip(self, request: Request) -> str:
        """Trust forwarded addresses only when the immediate peer is trusted."""
        # pylint: disable=too-many-return-statements
        if self.configuration is None:
            # Direct middleware use falls back to the peer address; structured
            # setup can trust forwarding headers only through explicit proxies.
            return get_ip_address(request)
        peer = request.client.host if request.client else None
        if peer is None:
            return "Unknown IP"
        try:
            peer_address = ipaddress.ip_address(peer)
        except ValueError:
            return "Unknown IP"
        if not self.trusted_proxies or not any(
            peer_address in network for network in self.trusted_proxies
        ):
            return str(peer_address)
        forwarded = request.headers.get("x-forwarded-for", "")
        if not forwarded:
            return str(peer_address)
        try:
            hops = [ipaddress.ip_address(part.strip()) for part in forwarded.split(",")]
        except ValueError:
            return str(peer_address)
        for hop in reversed(hops):
            if not any(hop in net for net in self.trusted_proxies):
                return str(hop)
        return str(hops[0])

    @staticmethod
    def _log_sql_queries(
        test_queries: Optional[List[Dict]] = None,
        *,
        max_bytes: Optional[int] = None,
        truncated: bool = False,
    ) -> Optional[str]:
        """Format captured SQL queries without exceeding the configured limit.

        SQL text can contain credentials and personal data. This method is reached only
        when SQL diagnostics are explicitly enabled.
        """
        queries = get_queries() if test_queries is None else test_queries
        if not queries and not truncated:
            return None

        lines = [f"{len(queries)} SQL QUERIES EXECUTED\\n"]
        for index, query in enumerate(queries, start=1):
            lines.append(
                f"\\t\\tQuery{index}={{'Time': {query['time']}(s), "
                f"'Query': [{query['sql']}]}}\\n\\t"
            )
        if truncated:
            lines.append("<SQL query capture truncated>\\n")
        result = "".join(lines)
        if max_bytes is not None and len(result.encode("utf-8")) > max_bytes:
            return "<oversized SQL log>"
        return result

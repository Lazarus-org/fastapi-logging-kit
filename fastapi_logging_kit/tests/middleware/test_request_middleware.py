import asyncio
import logging
import sys
from uuid import UUID

from typing import Any, Callable, Dict, List

import pytest
from starlette.requests import Request

from fastapi_logging_kit.contextvar import manager
from fastapi_logging_kit.middleware import RequestLogMiddleware
from fastapi_logging_kit.settings import settings_manager
from fastapi_logging_kit.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON
from fastapi_logging_kit.utils.sql import record_query

pytestmark = [
    pytest.mark.middleware,
    pytest.mark.request_middleware,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]

LOGGER_NAME = "fastapi_logging_kit.middleware.request_middleware"


async def _send_plain_response(send: Callable[..., Any]) -> None:
    """Send a minimal, non-streaming 200 response."""
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"content-type", b"text/plain")],
        }
    )
    await send({"type": "http.response.body", "body": b"ok", "more_body": False})


class TestRequestLogMiddlewareBasics:
    """Test suite for the happy path of `RequestLogMiddleware`."""

    async def test_logs_request_started_and_finished(
        self,
        request_middleware: RequestLogMiddleware,
        scope_factory: Callable[..., Dict[str, Any]],
        asgi_caller: Callable[..., Any],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that a normal request logs both start and finish records."""
        caplog.set_level(logging.INFO, logger=LOGGER_NAME)

        messages = await asgi_caller(
            request_middleware, scope_factory(path="/items/", method="POST")
        )

        assert "REQUEST STARTED" in caplog.text
        assert "method=POST" in caplog.text
        assert "path=/items/" in caplog.text
        assert "REQUEST FINISHED" in caplog.text
        assert "status_code=200" in caplog.text
        assert "content_type=[text/plain]" in caplog.text
        assert [message["type"] for message in messages] == [
            "http.response.start",
            "http.response.body",
        ]

    async def test_logs_query_params_and_referrer(
        self,
        request_middleware: RequestLogMiddleware,
        scope_factory: Callable[..., Dict[str, Any]],
        asgi_caller: Callable[..., Any],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Query values are omitted by default to avoid accidental secret exposure."""
        caplog.set_level(logging.INFO, logger=LOGGER_NAME)

        await asgi_caller(
            request_middleware,
            scope_factory(
                query_string=b"page=2",
                headers={"Referer": "https://example.com/"},
            ),
        )

        assert "page=2" not in caplog.text
        assert "query_params=" not in caplog.text
        assert "https://example.com/" not in caplog.text

    async def test_generates_request_id_when_header_absent(
        self,
        scope_factory: Callable[..., Dict[str, Any]],
        asgi_caller: Callable[..., Any],
    ) -> None:
        """Test that a UUID request ID is generated without a header."""
        captured: Dict[str, Any] = {}

        async def app(scope: Any, receive: Any, send: Any) -> None:
            """Capture the bound context, then respond."""
            captured.update(manager.get_contextvars())
            await _send_plain_response(send)

        await asgi_caller(RequestLogMiddleware(app), scope_factory())

        assert UUID(captured["request_id"])

    async def test_reuses_supplied_request_id_header(
        self,
        scope_factory: Callable[..., Dict[str, Any]],
        asgi_caller: Callable[..., Any],
    ) -> None:
        """Test that an inbound `X-Request-ID` header is reused."""
        captured: Dict[str, Any] = {}

        async def app(scope: Any, receive: Any, send: Any) -> None:
            """Capture the bound context, then respond."""
            captured.update(manager.get_contextvars())
            await _send_plain_response(send)

        await asgi_caller(
            RequestLogMiddleware(app),
            scope_factory(headers={"X-Request-ID": "client-supplied-id"}),
        )

        assert captured["request_id"] == "client-supplied-id"

    async def test_binds_context_during_request_and_clears_after(
        self,
        scope_factory: Callable[..., Dict[str, Any]],
        asgi_caller: Callable[..., Any],
    ) -> None:
        """Test that context variables are bound then released."""
        captured: Dict[str, Any] = {}

        async def app(scope: Any, receive: Any, send: Any) -> None:
            """Capture the bound context, then respond."""
            captured.update(manager.get_contextvars())
            await _send_plain_response(send)

        await asgi_caller(
            RequestLogMiddleware(app),
            scope_factory(headers={"User-Agent": "pytest-agent/1.0"}),
        )

        assert captured["ip_address"] == "127.0.0.1"
        assert captured["user_agent"] == "pytest-agent/1.0"
        assert "request_id" in captured

        remaining = manager.get_contextvars()

        assert "request_id" not in remaining
        assert "ip_address" not in remaining
        assert "user_agent" not in remaining

    async def test_logs_authenticated_user(
        self,
        scope_factory: Callable[..., Dict[str, Any]],
        asgi_caller: Callable[..., Any],
        dummy_user: Any,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that the user on the scope appears in the finish record."""
        caplog.set_level(logging.INFO, logger=LOGGER_NAME)

        async def app(scope: Any, receive: Any, send: Any) -> None:
            """Respond with a plain 200."""
            await _send_plain_response(send)

        await asgi_caller(RequestLogMiddleware(app), scope_factory(user=dummy_user))

        assert "user=[tester (ID:1)]" in caplog.text

    async def test_finalizes_when_app_sends_nothing(
        self,
        scope_factory: Callable[..., Dict[str, Any]],
        asgi_caller: Callable[..., Any],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that an app sending no response is still finalized."""
        caplog.set_level(logging.INFO, logger=LOGGER_NAME)

        async def app(scope: Any, receive: Any, send: Any) -> None:
            """Send nothing at all."""

        await asgi_caller(RequestLogMiddleware(app), scope_factory())

        assert "REQUEST FINISHED" in caplog.text
        assert "status_code=0" in caplog.text
        assert "content_type=[Unknown]" in caplog.text


class TestRequestLogMiddlewareStreaming:
    """Test suite for streaming responses handled by the middleware."""

    async def test_logs_streaming_started_and_finished(
        self,
        scope_factory: Callable[..., Dict[str, Any]],
        asgi_caller: Callable[..., Any],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that a multi-chunk response logs streaming boundaries."""
        caplog.set_level(logging.INFO, logger=LOGGER_NAME)

        async def app(scope: Any, receive: Any, send: Any) -> None:
            """Send a response body in two chunks."""
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [(b"content-type", b"text/event-stream")],
                }
            )
            await send(
                {"type": "http.response.body", "body": b"one", "more_body": True}
            )
            await send(
                {"type": "http.response.body", "body": b"two", "more_body": False}
            )

        await asgi_caller(RequestLogMiddleware(app), scope_factory())

        assert "Streaming started" in caplog.text
        assert "Streaming finished" in caplog.text
        assert "REQUEST FINISHED" in caplog.text

    async def test_non_streaming_response_logs_no_streaming_records(
        self,
        request_middleware: RequestLogMiddleware,
        scope_factory: Callable[..., Dict[str, Any]],
        asgi_caller: Callable[..., Any],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that a single-chunk response logs no streaming records."""
        caplog.set_level(logging.INFO, logger=LOGGER_NAME)

        await asgi_caller(request_middleware, scope_factory())

        assert "Streaming started" not in caplog.text
        assert "Streaming finished" not in caplog.text


class TestRequestLogMiddlewareErrors:
    """Test suite for error and cancellation handling."""

    async def test_exception_is_finalized_and_reraised(
        self,
        scope_factory: Callable[..., Dict[str, Any]],
        asgi_caller: Callable[..., Any],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that an application error still finalizes the request."""
        caplog.set_level(logging.INFO, logger=LOGGER_NAME)

        async def app(scope: Any, receive: Any, send: Any) -> None:
            """Fail before sending anything."""
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            await asgi_caller(RequestLogMiddleware(app), scope_factory())

        assert "REQUEST FINISHED" in caplog.text
        assert "Streaming failed" not in caplog.text

    async def test_exception_mid_stream_logs_streaming_failure(
        self,
        scope_factory: Callable[..., Dict[str, Any]],
        asgi_caller: Callable[..., Any],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that failing after a chunk logs a streaming failure."""
        caplog.set_level(logging.INFO, logger=LOGGER_NAME)

        async def app(scope: Any, receive: Any, send: Any) -> None:
            """Send one chunk, then fail."""
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [(b"content-type", b"text/plain")],
                }
            )
            await send(
                {"type": "http.response.body", "body": b"partial", "more_body": True}
            )
            raise RuntimeError("stream exploded")

        with pytest.raises(RuntimeError, match="stream exploded"):
            await asgi_caller(RequestLogMiddleware(app), scope_factory())

        assert "Streaming failed" in caplog.text
        assert "REQUEST FINISHED" in caplog.text

    async def test_cancelled_error_is_logged_and_reraised(
        self,
        scope_factory: Callable[..., Dict[str, Any]],
        asgi_caller: Callable[..., Any],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that a client disconnect is logged and the error re-raised."""
        caplog.set_level(logging.INFO, logger=LOGGER_NAME)

        async def app(scope: Any, receive: Any, send: Any) -> None:
            """Simulate a client disconnect."""
            raise asyncio.CancelledError()

        with pytest.raises(asyncio.CancelledError):
            await asgi_caller(RequestLogMiddleware(app), scope_factory())

        assert "Request was cancelled" in caplog.text
        assert "REQUEST FINISHED" not in caplog.text
        assert "request_id" not in manager.get_contextvars()


class TestRequestLogMiddlewareFinalization:
    """Test suite for `_finalize_request` behaviour."""

    def test_finalize_request_is_idempotent(
        self,
        request_middleware: RequestLogMiddleware,
        request_factory: Callable[..., Request],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that finalizing twice logs the finish record only once."""
        caplog.set_level(logging.INFO, logger=LOGGER_NAME)

        state: Dict[str, object] = {
            "status_code": 200,
            "content_type": "text/plain",
            "chunks": 1,
            "finalized": False,
        }
        request = request_factory()

        request_middleware._finalize_request(request, state, 0.0)
        request_middleware._finalize_request(request, state, 0.0)

        finish_records = [
            record
            for record in caplog.records
            if "REQUEST FINISHED" in record.getMessage()
        ]

        assert len(finish_records) == 1
        assert state["finalized"] is True


class TestRequestLogMiddlewareSqlLogging:
    """Test suite for the optional SQL query reporting."""

    async def test_reports_recorded_queries(
        self,
        scope_factory: Callable[..., Dict[str, Any]],
        asgi_caller: Callable[..., Any],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that queries run during the request are reported."""
        caplog.set_level(logging.INFO, logger=LOGGER_NAME)
        settings_manager.load({"LOG_SQL_QUERIES_ENABLE": True})

        async def app(scope: Any, receive: Any, send: Any) -> None:
            """Record a query, then respond."""
            record_query("SELECT * FROM users", 0.02)
            await _send_plain_response(send)

        middleware = RequestLogMiddleware(app)
        assert middleware.log_sql is True

        await asgi_caller(middleware, scope_factory())

        assert "1 SQL QUERIES EXECUTED" in caplog.text
        assert "SELECT * FROM users" in caplog.text

    async def test_reports_nothing_without_queries(
        self,
        scope_factory: Callable[..., Dict[str, Any]],
        asgi_caller: Callable[..., Any],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that no query report is emitted when nothing ran."""
        caplog.set_level(logging.INFO, logger=LOGGER_NAME)
        settings_manager.load({"LOG_SQL_QUERIES_ENABLE": True})

        async def app(scope: Any, receive: Any, send: Any) -> None:
            """Respond without touching the database."""
            await _send_plain_response(send)

        await asgi_caller(RequestLogMiddleware(app), scope_factory())

        assert "SQL QUERIES EXECUTED" not in caplog.text
        assert "REQUEST FINISHED" in caplog.text

    def test_log_sql_queries_returns_none_without_queries(self) -> None:
        """Test that the formatter returns None when nothing was recorded."""
        assert RequestLogMiddleware._log_sql_queries() is None

    def test_log_sql_queries_formats_injected_queries(self) -> None:
        """Test that injected test queries are formatted for logging."""
        test_queries: List[Dict[str, str]] = [
            {"time": "0.02", "sql": "SELECT * FROM table_name"},
            {"time": "0.05", "sql": "SELECT * FROM other_table"},
        ]

        result = RequestLogMiddleware._log_sql_queries(test_queries)

        assert result is not None
        assert result.startswith("2 SQL QUERIES EXECUTED")
        assert "Query1={'Time': 0.02(s), 'Query': [SELECT * FROM table_name]}" in result
        assert "Query2={'Time': 0.05(s), 'Query': [SELECT * FROM other_table]}" in result

    def test_log_sql_disabled_by_default(self) -> None:
        """Test that SQL reporting is off unless explicitly enabled."""
        settings_manager.load({"LOG_SQL_QUERIES_ENABLE": False})

        async def app(scope: Any, receive: Any, send: Any) -> None:
            """Do nothing."""

        assert RequestLogMiddleware(app).log_sql is False


async def test_chunked_request_body_is_forwarded_unchanged_and_captured_bounded(
    scope_factory, asgi_caller, caplog
):
    """Request diagnostics observe ASGI chunks without changing app input."""
    from fastapi_logging_kit.settings.contract import compile_settings

    caplog.set_level(logging.INFO, logger=LOGGER_NAME)
    received = bytearray()
    body_chunks = [b'{"username":', b'"alice",', b'"password":"chunk-secret"}']

    async def app(scope, receive, send):
        while True:
            message = await receive()
            received.extend(message.get("body", b""))
            if not message.get("more_body", False):
                break
        await _send_plain_response(send)

    config = compile_settings({
        "REQUEST_LOGGING": {
            "REQUEST_BODY_ENABLED": True,
            "MAX_BODY_BYTES": 128,
        }
    })["REQUEST_LOGGING"]
    middleware = RequestLogMiddleware(app, config=config)
    sent = await asgi_caller(
        middleware,
        scope_factory(
            method="POST",
            headers={"Content-Type": "application/json"},
        ),
        body_chunks=body_chunks,
    )
    assert bytes(received) == b"".join(body_chunks)
    assert [message["type"] for message in sent] == [
        "http.response.start", "http.response.body"
    ]
    assert '"username":"alice"' in caplog.text
    assert "chunk-secret" not in caplog.text
    assert "[REDACTED]" in caplog.text


async def test_streaming_finish_is_not_logged_when_final_send_fails(
    scope_factory, caplog
):
    """A failed final ASGI send must not be reported as a finished stream."""
    from fastapi_logging_kit.settings.contract import compile_settings

    caplog.set_level(logging.INFO, logger=LOGGER_NAME)

    async def app(scope, receive, send):
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"content-type", b"text/plain")],
        })
        await send({"type": "http.response.body", "body": b"part", "more_body": True})
        await send({"type": "http.response.body", "body": b"done", "more_body": False})

    config = compile_settings(
        {"REQUEST_LOGGING": {"LOG_STREAMING_EVENTS": True}}
    )["REQUEST_LOGGING"]
    middleware = RequestLogMiddleware(app, config=config)

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def failing_send(message):
        if (
            message["type"] == "http.response.body"
            and not message.get("more_body", False)
        ):
            raise RuntimeError("downstream send failed")

    with pytest.raises(RuntimeError, match="downstream send failed"):
        await middleware(scope_factory(), receive, failing_send)

    assert "Streaming started" in caplog.text
    assert "Streaming failed" in caplog.text
    assert "Streaming finished" not in caplog.text


async def test_legacy_middleware_does_not_trust_forwarded_for_by_default(
    scope_factory, asgi_caller
):
    captured = {}

    async def app(scope, receive, send):
        captured.update(manager.get_contextvars())
        await _send_plain_response(send)

    await asgi_caller(
        RequestLogMiddleware(app),
        scope_factory(
            client=("192.0.2.10", 9000),
            headers={"X-Forwarded-For": "203.0.113.50"},
        ),
    )
    assert captured["ip_address"] == "192.0.2.10"


def test_finalize_request_skips_expensive_diagnostics_when_info_is_disabled(
    request_middleware, request_factory, caplog
):
    state = {
        "status_code": 200,
        "content_type": "application/json",
        "chunks": 1,
        "finalized": False,
    }
    with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
        request_middleware._finalize_request(request_factory(), state, 0.0)
    assert state["finalized"] is True
    assert "REQUEST FINISHED" not in caplog.text



class TestStructuredSQLDiagnostics:
    """SQL request diagnostics exposed by the structured v1 configuration."""

    async def test_structured_configuration_captures_queries(
        self, scope_factory, asgi_caller, caplog
    ):
        caplog.set_level(logging.INFO, logger=LOGGER_NAME)

        async def app(scope, receive, send):
            record_query("SELECT * FROM accounts", 0.012)
            await _send_plain_response(send)

        middleware = RequestLogMiddleware(
            app,
            config={"LOG_SQL_QUERIES": True},
        )
        await asgi_caller(middleware, scope_factory())
        assert "1 SQL QUERIES EXECUTED" in caplog.text
        assert "SELECT * FROM accounts" in caplog.text

    async def test_query_capture_is_bounded_by_count(
        self, scope_factory, asgi_caller, caplog
    ):
        caplog.set_level(logging.INFO, logger=LOGGER_NAME)

        async def app(scope, receive, send):
            record_query("SELECT first", 0.01)
            record_query("SELECT second", 0.02)
            await _send_plain_response(send)

        middleware = RequestLogMiddleware(
            app,
            config={"LOG_SQL_QUERIES": True, "MAX_SQL_QUERIES": 1},
        )
        await asgi_caller(middleware, scope_factory())
        assert "1 SQL QUERIES EXECUTED" in caplog.text
        assert "SELECT first" in caplog.text
        assert "SELECT second" not in caplog.text
        assert "SQL query capture truncated" in caplog.text

    async def test_query_capture_is_bounded_by_bytes(
        self, scope_factory, asgi_caller, caplog
    ):
        caplog.set_level(logging.INFO, logger=LOGGER_NAME)

        async def app(scope, receive, send):
            record_query("SELECT a very long query statement", 0.01)
            await _send_plain_response(send)

        middleware = RequestLogMiddleware(
            app,
            config={"LOG_SQL_QUERIES": True, "MAX_SQL_BYTES": 32},
        )
        await asgi_caller(middleware, scope_factory())
        assert "<oversized SQL log>" in caplog.text
        assert "SELECT a very long query statement" not in caplog.text

    async def test_structured_sql_logging_is_disabled_by_default(
        self, scope_factory, asgi_caller, caplog
    ):
        caplog.set_level(logging.INFO, logger=LOGGER_NAME)

        async def app(scope, receive, send):
            record_query("SELECT private_data", 0.01)
            await _send_plain_response(send)

        middleware = RequestLogMiddleware(app, config={})
        await asgi_caller(middleware, scope_factory())
        assert "SELECT private_data" not in caplog.text
        assert "SQL QUERIES EXECUTED" not in caplog.text

    async def test_streaming_events_are_opt_in_for_structured_config(
        self, scope_factory, asgi_caller, caplog
    ):
        caplog.set_level(logging.INFO, logger=LOGGER_NAME)

        async def app(scope, receive, send):
            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"text/plain")],
            })
            await send({
                "type": "http.response.body",
                "body": b"one",
                "more_body": True,
            })
            await send({
                "type": "http.response.body",
                "body": b"two",
                "more_body": False,
            })

        middleware = RequestLogMiddleware(app, config={})
        await asgi_caller(middleware, scope_factory())
        assert "Streaming started" not in caplog.text
        assert "Streaming finished" not in caplog.text

        caplog.clear()
        middleware = RequestLogMiddleware(
            app, config={"LOG_STREAMING_EVENTS": True}
        )
        await asgi_caller(middleware, scope_factory())
        assert "Streaming started" in caplog.text
        assert "Streaming finished" in caplog.text

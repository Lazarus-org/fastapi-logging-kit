import sys
from typing import Any, Callable, Dict, List

import pytest

from fast_logging.middleware.base import BaseMiddleware, get_header
from fast_logging.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON

pytestmark = [
    pytest.mark.middleware,
    pytest.mark.base_middleware,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


async def _noop_app(scope: Any, receive: Any, send: Any) -> None:
    """A trivial ASGI application that does nothing."""


class _CallableApp:
    """A class-based ASGI application used to exercise `__repr__`."""

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        """Do nothing."""


class TestBaseMiddlewareInitialization:
    """Test suite for `BaseMiddleware` construction and representation."""

    def test_stores_the_wrapped_app(self) -> None:
        """Test that the next application is stored on the instance."""
        middleware = BaseMiddleware(_noop_app)

        assert middleware.app is _noop_app

    def test_repr_uses_app_qualname(self) -> None:
        """Test that `__repr__` prefers the application's qualified name."""
        middleware = BaseMiddleware(_noop_app)

        assert repr(middleware) == f"<BaseMiddleware app={_noop_app.__qualname__}>"

    def test_repr_falls_back_to_class_name(self) -> None:
        """Test that `__repr__` uses the class name when no qualname exists."""
        middleware = BaseMiddleware(_CallableApp())

        assert repr(middleware) == "<BaseMiddleware app=_CallableApp>"


class TestBaseMiddlewareCall:
    """Test suite for the `BaseMiddleware.__call__` scope routing."""

    @pytest.mark.parametrize("scope_type", ["lifespan", "websocket"])
    async def test_non_http_scope_passes_through_untouched(
        self, scope_factory: Callable[..., Dict[str, Any]], scope_type: str
    ) -> None:
        """Test that non-HTTP scopes reach the wrapped app unchanged."""
        seen: List[Any] = []

        async def app(scope: Any, receive: Any, send: Any) -> None:
            """Record the exact arguments the middleware forwarded."""
            seen.append((scope, receive, send))

        async def receive() -> Dict[str, Any]:
            """A stand-in receive channel."""
            return {"type": "noop"}

        async def send(message: Dict[str, Any]) -> None:
            """A stand-in send channel."""

        scope = scope_factory(scope_type=scope_type)
        middleware = BaseMiddleware(app)

        await middleware(scope, receive, send)

        assert seen == [(scope, receive, send)]

    async def test_http_scope_reaches_dispatch(
        self, scope_factory: Callable[..., Dict[str, Any]], asgi_caller: Callable[..., Any]
    ) -> None:
        """Test that an HTTP scope is handed to `dispatch`."""
        dispatched: List[Any] = []

        class _Subclass(BaseMiddleware):
            """A middleware recording the scopes it dispatches."""

            async def dispatch(self, scope: Any, receive: Any, send: Any) -> None:
                """Record the dispatched scope."""
                dispatched.append(scope)

        scope = scope_factory()

        await asgi_caller(_Subclass(_noop_app), scope)

        assert dispatched == [scope]

    async def test_base_dispatch_raises_not_implemented(
        self, scope_factory: Callable[..., Dict[str, Any]], asgi_caller: Callable[..., Any]
    ) -> None:
        """Test that the base `dispatch` refuses to handle HTTP scopes."""
        middleware = BaseMiddleware(_noop_app)

        with pytest.raises(NotImplementedError, match="must be implemented by subclass"):
            await asgi_caller(middleware, scope_factory())


class TestGetHeader:
    """Test suite for the `get_header` helper."""

    def test_returns_present_header(self) -> None:
        """Test that a matching header value is decoded and returned."""
        message = {
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"Content-Type", b"application/json")],
        }

        assert get_header(message, "content-type") == "application/json"

    def test_returns_unknown_for_absent_header(self) -> None:
        """Test that a missing header yields the unknown marker."""
        message = {
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"x-other", b"value")],
        }

        assert get_header(message, "content-type") == "Unknown"

    def test_returns_unknown_when_headers_key_is_missing(self) -> None:
        """Test that a message carrying no headers yields the marker."""
        assert get_header({"type": "http.response.start"}, "content-type") == "Unknown"

    def test_returns_unknown_when_headers_is_none(self) -> None:
        """Test that an explicit None headers value yields the marker."""
        assert get_header({"headers": None}, "content-type") == "Unknown"

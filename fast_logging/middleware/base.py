from typing import Any, MutableMapping

from starlette.types import ASGIApp, Message, Receive, Scope, Send


class BaseMiddleware:
    """Base class for the ``fast_logging`` ASGI middleware.

    ``django_logging`` had to support Django's dual sync/async middleware
    protocol, branching between ``__sync_call__`` and ``__acall__``
    depending on whether ``get_response`` was a coroutine function. ASGI
    has no such split — every application is async — so this base class
    is correspondingly simpler: it forwards non-HTTP scopes (lifespan,
    websocket) untouched and hands HTTP scopes to :meth:`dispatch`.

    Attributes:
        app (ASGIApp): The next application in the middleware stack.

    """

    def __init__(self, app: ASGIApp) -> None:
        """Initializes the middleware.

        Args:
            app (ASGIApp): The next ASGI application to call.

        """
        self.app = app

    def __repr__(self) -> str:
        """Provides a string representation of the middleware."""
        app = getattr(self.app, "__qualname__", self.app.__class__.__name__)
        return f"<{self.__class__.__qualname__} app={app}>"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handles an incoming ASGI event.

        Non-HTTP scopes are passed straight through so websocket and
        lifespan traffic is never touched.

        Args:
            scope (Scope): The ASGI connection scope.
            receive (Receive): The ASGI receive channel.
            send (Send): The ASGI send channel.

        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        await self.dispatch(scope, receive, send)

    async def dispatch(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handles an HTTP scope.

        Args:
            scope (Scope): The ASGI connection scope.
            receive (Receive): The ASGI receive channel.
            send (Send): The ASGI send channel.

        Raises:
            NotImplementedError: Always, unless overridden by a subclass.

        """
        raise NotImplementedError("dispatch must be implemented by subclass")


def get_header(message: MutableMapping[str, Any], name: str) -> str:
    """Read a header value out of an ASGI ``http.response.start`` message.

    Args:
        message (MutableMapping[str, Any]): The response start message.
        name (str): The header name, lower-cased.

    Returns:
        str: The decoded header value, or ``"Unknown"`` when absent.

    """
    target = name.lower().encode("latin-1")
    for key, value in message.get("headers") or []:
        if key.lower() == target:
            return value.decode("latin-1")
    return "Unknown"


__all__ = ["BaseMiddleware", "Message", "get_header"]

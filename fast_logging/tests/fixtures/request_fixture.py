from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

import pytest
from starlette.requests import Request

from fast_logging.middleware import RequestLogMiddleware


class DummyUser:
    """A stand-in for an authenticated user on the ASGI scope.

    Attributes:
        username (str): The user's name.
        id (int): The user's primary key.
        is_authenticated (bool): Whether the user is authenticated.
        is_superuser (bool): Whether the user has superuser rights.

    """

    def __init__(
        self,
        username: str = "tester",
        id: int = 1,  # pylint: disable=redefined-builtin
        is_authenticated: bool = True,
        is_superuser: bool = False,
    ) -> None:
        """Initialize the dummy user."""
        self.username = username
        self.id = id
        self.is_authenticated = is_authenticated
        self.is_superuser = is_superuser


def build_scope(
    path: str = "/test/",
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    query_string: bytes = b"",
    client: Optional[Tuple[str, int]] = ("127.0.0.1", 5000),
    scope_type: str = "http",
    user: Any = None,
) -> Dict[str, Any]:
    """Build an ASGI scope for testing.

    Args:
        path (str): The request path.
        method (str): The HTTP method.
        headers (Optional[Dict[str, str]]): Request headers.
        query_string (bytes): The raw query string.
        client (Optional[Tuple[str, int]]): The peer address.
        scope_type (str): The ASGI scope type.
        user (Any): A user object to place on the scope.

    Returns:
        Dict[str, Any]: The constructed scope.

    """
    encoded_headers = [
        (key.lower().encode("latin-1"), value.encode("latin-1"))
        for key, value in (headers or {}).items()
    ]

    scope: Dict[str, Any] = {
        "type": scope_type,
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": query_string,
        "root_path": "",
        "headers": encoded_headers,
        "client": client,
        "server": ("testserver", 80),
    }
    if user is not None:
        scope["user"] = user

    return scope


@pytest.fixture
def scope_factory() -> Callable[..., Dict[str, Any]]:
    """Return the :func:`build_scope` helper.

    Returns:
        Callable[..., Dict[str, Any]]: The scope builder.

    """
    return build_scope


@pytest.fixture
def request_factory() -> Callable[..., Request]:
    """Return a callable building Starlette requests.

    Returns:
        Callable[..., Request]: The request builder.

    """

    def factory(**kwargs: Any) -> Request:
        return Request(build_scope(**kwargs))

    return factory


@pytest.fixture
def dummy_user() -> DummyUser:
    """Return an authenticated non-superuser.

    Returns:
        DummyUser: The user.

    """
    return DummyUser()


@pytest.fixture
def superuser() -> DummyUser:
    """Return an authenticated superuser.

    Returns:
        DummyUser: The user.

    """
    return DummyUser(username="root", id=99, is_superuser=True)


async def call_asgi(
    app: Any,
    scope: Dict[str, Any],
    body_chunks: Optional[List[bytes]] = None,
) -> List[Dict[str, Any]]:
    """Drive an ASGI application and collect the messages it sends.

    Args:
        app (Any): The ASGI application to call.
        scope (Dict[str, Any]): The connection scope.
        body_chunks (Optional[List[bytes]]): Request body chunks.

    Returns:
        List[Dict[str, Any]]: Every message the application sent.

    """
    received = list(body_chunks or [b""])
    sent: List[Dict[str, Any]] = []

    async def receive() -> Dict[str, Any]:
        chunk = received.pop(0) if received else b""
        return {
            "type": "http.request",
            "body": chunk,
            "more_body": bool(received),
        }

    async def send(message: Dict[str, Any]) -> None:
        sent.append(message)

    await app(scope, receive, send)
    return sent


@pytest.fixture
def asgi_caller() -> Callable[..., Any]:
    """Return the :func:`call_asgi` helper.

    Returns:
        Callable[..., Any]: The ASGI driver.

    """
    return call_asgi


@pytest.fixture
def request_middleware() -> Iterator[RequestLogMiddleware]:
    """Return a RequestLogMiddleware wrapping a trivial application.

    Yields:
        RequestLogMiddleware: The middleware instance.

    """

    async def app(scope: Dict[str, Any], receive: Any, send: Any) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"text/plain")],
            }
        )
        await send({"type": "http.response.body", "body": b"ok", "more_body": False})

    yield RequestLogMiddleware(app)

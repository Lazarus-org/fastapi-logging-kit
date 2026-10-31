"""Helpers for pulling client details out of a Starlette/FastAPI request.

``django_logging`` read these from ``request.META`` and exposed them as
static methods on ``RequestLogMiddleware``. Starlette carries the same
information on ``request.headers`` and ``request.client``, and keeping
the helpers in their own module lets the email handler use them without
importing the middleware.

"""

import ipaddress
from typing import Any, Optional

UNKNOWN_IP = "Unknown IP"
UNKNOWN_USER_AGENT = "Unknown User Agent"


def get_ip_address(request: Any) -> str:
    """Return the immediate ASGI peer address without trusting proxy headers.

    Forwarded addresses are security-sensitive and must be resolved by the
    middleware using an explicit trusted-proxy policy. This helper is also used
    by email notifications, where no proxy policy is available, so it always
    falls back to the transport peer.
    """
    client = getattr(request, "client", None)
    host = getattr(client, "host", None) if client is not None else None
    if not isinstance(host, str) or not host:
        return UNKNOWN_IP
    try:
        return str(ipaddress.ip_address(host))
    except ValueError:
        return UNKNOWN_IP


def get_user_agent(request: Any) -> str:
    """Retrieve the client's user agent from the request.

    Args:
        request (Any): The incoming request.

    Returns:
        str: The client's user agent, or ``"Unknown User Agent"``.

    """
    return request.headers.get("user-agent", UNKNOWN_USER_AGENT)


def get_request_id(request: Any) -> Optional[str]:
    """Retrieve the request ID supplied by the client, if any.

    Args:
        request (Any): The incoming request.

    Returns:
        Optional[str]: The value of the ``X-Request-ID`` header, or None.

    """
    return request.headers.get("x-request-id")


def get_user(request: Any) -> str:
    """Describe the authenticated user behind the request.

    FastAPI has no built-in authentication, so this looks for a ``user``
    on the ASGI scope — the convention used by Starlette's
    ``AuthenticationMiddleware`` and most FastAPI auth extensions. A user
    is considered authenticated when it exposes a truthy
    ``is_authenticated`` attribute, or when it is any other non-None
    object without one.

    Args:
        request (Any): The incoming request.

    Returns:
        str: A ``"[username (ID:pk)]"`` style description, or
        ``"Anonymous"`` when no user is present.

    """
    scope = getattr(request, "scope", None) or {}
    user = scope.get("user")

    if user is None:
        return "Anonymous"

    is_authenticated = getattr(user, "is_authenticated", True)
    if not is_authenticated:
        return "Anonymous"

    username = None
    for attribute in ("username", "email", "display_name", "name"):
        username = getattr(user, attribute, None)
        if username:
            break

    if not username:
        username = str(user)

    identifier = getattr(user, "id", None)
    if identifier is None:
        identifier = getattr(user, "pk", None)

    if identifier is None:
        return f"[{username}]"

    return f"[{username} (ID:{identifier})]"

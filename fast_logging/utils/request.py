"""Helpers for pulling client details out of a Starlette/FastAPI request.

``django_logging`` read these from ``request.META`` and exposed them as
static methods on ``RequestLogMiddleware``. Starlette carries the same
information on ``request.headers`` and ``request.client``, and keeping
the helpers in their own module lets the email handler use them without
importing the middleware.

"""

from typing import Any, Optional

UNKNOWN_IP = "Unknown IP"
UNKNOWN_USER_AGENT = "Unknown User Agent"


def get_ip_address(request: Any) -> str:
    """Retrieve the client's IP address from the request.

    The ``X-Forwarded-For`` header wins when present, using its first
    entry; otherwise the address of the immediate peer is used.

    Args:
        request (Any): The incoming request.

    Returns:
        str: The client's IP address, or ``"Unknown IP"``.

    """
    # Return the cached IP address if it exists
    cached = getattr(request, "ip_address", None)
    if cached:
        return str(cached)

    forwarded_for = request.headers.get("x-forwarded-for")

    if forwarded_for:
        # Split on commas and strip whitespace from each part
        ip_address_list = [ip.strip() for ip in forwarded_for.split(",") if ip.strip()]
        # Use the first valid IP in the list
        if ip_address_list:
            return ip_address_list[0]

    # Fallback to the peer address if no valid X-Forwarded-For header
    client = getattr(request, "client", None)
    if client is not None and getattr(client, "host", None):
        return str(client.host)

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

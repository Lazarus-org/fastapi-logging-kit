"""The LogiBoard router.

``django_logging`` exposed LogiBoard as a ``TemplateView`` wired up in
``urls.py`` and restricted to superusers. The FastAPI equivalent is an
``APIRouter`` plus a ``StaticFiles`` mount for the packaged assets.

FastAPI has no built-in auth, so access control is a replaceable
predicate: :func:`set_permission_check` installs your own callable. The
default reads ``is_superuser`` off ``scope["user"]`` and denies access
when no user is present, matching how Django's ``AnonymousUser`` would
fail the same check.

"""

import inspect
from threading import RLock
from typing import Any, Callable, Optional

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from starlette.staticfiles import StaticFiles

from fastapi_logging_kit.templating import STATIC_DIR, STATIC_URL_PREFIX, render_to_string

PermissionCheck = Callable[[Request], bool]

router = APIRouter(tags=["fastapi-logging-kit"])


def default_permission_check(request: Request) -> bool:
    """Allow access only to a superuser on the ASGI scope.

    Args:
        request (Request): The incoming request.

    Returns:
        bool: True when the request carries a superuser, else False.

    """
    user = request.scope.get("user")
    if user is None:
        return False

    return bool(getattr(user, "is_superuser", False))


_permission_check: PermissionCheck = default_permission_check
_permission_lock = RLock()


def set_permission_check(
    check: Optional[PermissionCheck], *, app: Optional[Any] = None
) -> None:
    """Set a process-wide or application-scoped LogiBoard permission predicate.

    The callback must be synchronous and return a real ``bool``; invalid or
    awaitable results fail closed. Passing ``app`` isolates the policy to that
    FastAPI application. Without it, the process-wide default is updated.
    Passing ``None`` restores the default predicate (or the process-wide policy
    for an app override).
    """
    if check is not None and not callable(check):
        raise TypeError("permission check must be callable or None")
    if check is not None and (
        inspect.iscoroutinefunction(check)
        or inspect.iscoroutinefunction(getattr(check, "__call__", None))
    ):
        raise TypeError("LogiBoard permission checks must be synchronous")
    if app is not None:
        app.state._fastapi_logging_kit_permission_check = check
        return

    global _permission_check  # pylint: disable=global-statement
    with _permission_lock:
        _permission_check = check if check is not None else default_permission_check


def get_permission_check(app: Optional[Any] = None) -> PermissionCheck:
    """Return the permission predicate for *app* or the process default."""
    if app is not None:
        app_check = getattr(app.state, "_fastapi_logging_kit_permission_check", None)
        if app_check is not None:
            return app_check
    with _permission_lock:
        return _permission_check


def _permission_is_allowed(request: Request) -> bool:
    """Evaluate the synchronous permission predicate without fail-open results."""
    result = get_permission_check(request.app)(request)
    if inspect.isawaitable(result):
        if inspect.iscoroutine(result):
            result.close()
        raise TypeError("LogiBoard permission checks must return bool synchronously")
    if not isinstance(result, bool):
        raise TypeError("LogiBoard permission checks must return bool synchronously")
    return result


@router.get("/log-iboard/", response_class=HTMLResponse, name="log-iboard")
async def log_iboard(request: Request) -> HTMLResponse:
    """Render the LogiBoard page for permitted users.

    Users failing the permission check are shown an error response page
    with a 403 status code.

    Args:
        request (Request): The incoming request.

    Returns:
        HTMLResponse: The rendered LogiBoard page, or a 403 error page.

    """
    if _permission_is_allowed(request):
        return HTMLResponse(render_to_string("log_iboard.html"))

    return HTMLResponse(
        render_to_string(
            "error_response.html",
            {
                "title": "Access Denied",
                "message": "You do not have permission to view this page.",
            },
        ),
        status_code=403,
    )


def mount_static(app: Any) -> None:
    """Mount the packaged LogiBoard assets once on *app*.

    Repeated setup calls are harmless. An application-owned route already
    occupying the package's static URL is treated as a configuration conflict
    rather than silently shadowed.
    """
    routes = getattr(app, "routes", ())
    for route in routes:
        route_name = getattr(route, "name", None)
        route_path = getattr(route, "path", None)
        if route_name == "fastapi-logging-kit-static":
            if route_path == STATIC_URL_PREFIX:
                return
            raise RuntimeError(
                "The route named 'fastapi-logging-kit-static' is registered at an "
                f"unexpected path: {route_path!r}."
            )
        if route_path == STATIC_URL_PREFIX:
            raise RuntimeError(
                f"Cannot mount LogiBoard assets: {STATIC_URL_PREFIX!r} "
                "is already registered by another route."
            )

    app.mount(
        STATIC_URL_PREFIX,
        StaticFiles(directory=STATIC_DIR),
        name="fastapi-logging-kit-static",
    )

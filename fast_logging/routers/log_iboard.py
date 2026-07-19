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

from typing import Any, Callable, Optional

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from starlette.staticfiles import StaticFiles

from fast_logging.templating import STATIC_DIR, STATIC_URL_PREFIX, render_to_string

PermissionCheck = Callable[[Any], bool]

router = APIRouter(tags=["fast-logging"])


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


def set_permission_check(check: Optional[PermissionCheck]) -> None:
    """Replace the predicate deciding who may view LogiBoard.

    Args:
        check (Optional[PermissionCheck]): A callable taking the request
            and returning True to allow access. Passing ``None`` restores
            the default superuser check.

    """
    global _permission_check  # pylint: disable=global-statement
    _permission_check = check if check is not None else default_permission_check


def get_permission_check() -> PermissionCheck:
    """Return the predicate currently guarding LogiBoard.

    Returns:
        PermissionCheck: The active permission check.

    """
    return _permission_check


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
    if _permission_check(request):
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
    """Mount the packaged LogiBoard static assets on *app*.

    Args:
        app (Any): The FastAPI application to mount the assets on.

    """
    app.mount(
        STATIC_URL_PREFIX,
        StaticFiles(directory=STATIC_DIR),
        name="fast-logging-static",
    )

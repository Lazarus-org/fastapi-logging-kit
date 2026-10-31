import sys
from typing import Any, Callable, Iterator, Optional

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from fastapi_logging_kit.routers.log_iboard import (
    default_permission_check,
    get_permission_check,
    mount_static,
    router,
    set_permission_check,
)
from fastapi_logging_kit.templating import STATIC_URL_PREFIX
from fastapi_logging_kit.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON
from fastapi_logging_kit.tests.fixtures import DummyUser

pytestmark = [
    pytest.mark.routers,
    pytest.mark.routers_log_iboard,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


@pytest.fixture(autouse=True)
def restore_permission_check() -> Iterator[None]:
    """Restore the default permission check after every test.

    Yields:
        None

    """
    yield
    set_permission_check(None)


def build_app(user: Optional[Any] = None) -> FastAPI:
    """Build an application serving LogiBoard for *user*.

    Args:
        user (Optional[Any]): A user placed on every request scope.

    Returns:
        FastAPI: The configured application.

    """
    app = FastAPI()
    app.include_router(router)
    mount_static(app)

    if user is not None:

        @app.middleware("http")
        async def attach_user(request: Request, call_next: Callable) -> Any:
            request.scope["user"] = user
            return await call_next(request)

    return app


class TestDefaultPermissionCheck:
    """Test suite for the `default_permission_check` predicate."""

    def test_denies_an_anonymous_request(
        self, request_factory: Callable[..., Request]
    ) -> None:
        """Test that a request without a user is denied.

        Args:
            request_factory (Callable[..., Request]): The request builder.

        """
        assert default_permission_check(request_factory()) is False

    def test_denies_a_non_superuser(
        self, request_factory: Callable[..., Request], dummy_user: DummyUser
    ) -> None:
        """Test that an ordinary authenticated user is denied.

        Args:
            request_factory (Callable[..., Request]): The request builder.
            dummy_user (DummyUser): A non-superuser.

        """
        assert default_permission_check(request_factory(user=dummy_user)) is False

    def test_allows_a_superuser(
        self, request_factory: Callable[..., Request], superuser: DummyUser
    ) -> None:
        """Test that a superuser is allowed.

        Args:
            request_factory (Callable[..., Request]): The request builder.
            superuser (DummyUser): A superuser.

        """
        assert default_permission_check(request_factory(user=superuser)) is True

    def test_denies_a_user_without_the_attribute(
        self, request_factory: Callable[..., Request]
    ) -> None:
        """Test that a user object lacking ``is_superuser`` is denied.

        Args:
            request_factory (Callable[..., Request]): The request builder.

        """
        assert default_permission_check(request_factory(user=object())) is False


class TestPermissionCheckRegistry:
    """Test suite for `set_permission_check` and `get_permission_check`."""

    def test_default_is_active_initially(self) -> None:
        """Test that the default predicate guards LogiBoard out of the box."""
        assert get_permission_check() is default_permission_check

    def test_installs_a_custom_predicate(self) -> None:
        """Test that a custom predicate replaces the default one."""

        def allow_everyone(request: Request) -> bool:
            return True

        set_permission_check(allow_everyone)
        assert get_permission_check() is allow_everyone

    def test_none_restores_the_default(self) -> None:
        """Test that passing None puts the default predicate back."""
        set_permission_check(lambda request: True)
        set_permission_check(None)
        assert get_permission_check() is default_permission_check


    def test_permission_check_can_be_scoped_to_an_application(self) -> None:
        """Test that applications can use independent access policies."""
        app = FastAPI()

        def allow_app(request: Request) -> bool:
            return True

        set_permission_check(allow_app, app=app)

        assert get_permission_check(app) is allow_app
        assert get_permission_check() is default_permission_check

    def test_clearing_application_override_restores_global_policy(self) -> None:
        """Test that clearing an app override falls back to the process policy."""
        app = FastAPI()

        def process_check(request: Request) -> bool:
            return True

        def app_check(request: Request) -> bool:
            return False

        set_permission_check(process_check)
        set_permission_check(app_check, app=app)
        set_permission_check(None, app=app)

        assert get_permission_check(app) is process_check

    def test_rejects_non_callable_permission_check(self) -> None:
        """Test that invalid permission callbacks fail immediately."""
        with pytest.raises(TypeError, match="must be callable"):
            set_permission_check("not callable")  # type: ignore[arg-type]

    def test_rejects_async_permission_check(self) -> None:
        """Test that async callbacks cannot accidentally grant access."""
        async def allow_everyone(request: Request) -> bool:
            return True

        with pytest.raises(TypeError, match="must be synchronous"):
            set_permission_check(allow_everyone)  # type: ignore[arg-type]


class TestLogiBoardView:
    """Test suite for the LogiBoard endpoint."""

    def test_anonymous_request_is_forbidden(self) -> None:
        """Test that an anonymous request receives the access denied page."""
        with TestClient(build_app()) as client:
            response = client.get("/log-iboard/")

        assert response.status_code == 403
        assert "Access Denied" in response.text
        assert "You do not have permission to view this page." in response.text

    def test_non_superuser_is_forbidden(self, dummy_user: DummyUser) -> None:
        """Test that an ordinary user receives the access denied page.

        Args:
            dummy_user (DummyUser): A non-superuser.

        """
        with TestClient(build_app(dummy_user)) as client:
            response = client.get("/log-iboard/")

        assert response.status_code == 403

    def test_superuser_sees_the_dashboard(self, superuser: DummyUser) -> None:
        """Test that a superuser receives the rendered LogiBoard page.

        Args:
            superuser (DummyUser): A superuser.

        """
        with TestClient(build_app(superuser)) as client:
            response = client.get("/log-iboard/")

        assert response.status_code == 200
        assert "Access Denied" not in response.text
        assert f"{STATIC_URL_PREFIX}/LogiBoard/css/app.css" in response.text

    def test_application_scoped_predicates_do_not_leak_between_apps(self) -> None:
        """Test that a custom policy on one app does not affect another."""
        allowed_app = build_app()
        denied_app = build_app()

        def allow(request: Request) -> bool:
            return True

        def deny(request: Request) -> bool:
            return False

        set_permission_check(allow, app=allowed_app)
        set_permission_check(deny, app=denied_app)

        with TestClient(allowed_app) as allowed_client:
            allowed = allowed_client.get("/log-iboard/")
        with TestClient(denied_app) as denied_client:
            denied = denied_client.get("/log-iboard/")

        assert allowed.status_code == 200
        assert denied.status_code == 403

    def test_a_custom_predicate_grants_access(self) -> None:
        """Test that an installed predicate decides who may view the page."""
        set_permission_check(lambda request: True)

        with TestClient(build_app()) as client:
            response = client.get("/log-iboard/")

        assert response.status_code == 200

    def test_sync_predicate_returning_coroutine_fails_closed(self) -> None:
        """Test that a dynamically returned coroutine cannot grant access."""
        async def allow_everyone() -> bool:
            return True

        def invalid_check(request: Request):
            return allow_everyone()

        set_permission_check(invalid_check)  # type: ignore[arg-type]

        with TestClient(build_app()) as client:
            with pytest.raises(TypeError, match="must return bool synchronously"):
                client.get("/log-iboard/")

        set_permission_check(None)

    def test_non_boolean_permission_result_fails_closed(self) -> None:
        """Test that truthy values other than bool cannot grant dashboard access."""
        set_permission_check(lambda request: "yes")  # type: ignore[arg-type]

        with TestClient(build_app()) as client:
            with pytest.raises(TypeError, match="must return bool synchronously"):
                client.get("/log-iboard/")

        set_permission_check(None)


class TestMountStatic:
    """Test suite for the `mount_static` helper."""

    def test_serves_a_packaged_asset(self) -> None:
        """Test that a packaged LogiBoard stylesheet is served."""
        with TestClient(build_app()) as client:
            response = client.get(f"{STATIC_URL_PREFIX}/LogiBoard/css/app.css")

        assert response.status_code == 200
        assert response.content

    def test_registers_a_named_mount(self) -> None:
        """Test that the mount is registered under its documented name."""
        app = FastAPI()
        mount_static(app)

        names = [getattr(route, "name", None) for route in app.routes]
        paths = [getattr(route, "path", None) for route in app.routes]
        assert "fastapi-logging-kit-static" in names
        assert STATIC_URL_PREFIX in paths

    def test_repeated_mount_is_idempotent(self) -> None:
        """Test that repeated setup does not register duplicate static mounts."""
        app = FastAPI()
        mount_static(app)
        mount_static(app)

        mounts = [
            route for route in app.routes
            if getattr(route, "name", None) == "fastapi-logging-kit-static"
        ]
        assert len(mounts) == 1

    def test_existing_path_conflict_fails_explicitly(self) -> None:
        """Test that an unrelated route cannot be silently shadowed."""
        app = FastAPI()
        app.add_route(STATIC_URL_PREFIX, lambda: None, name="application-static")

        with pytest.raises(RuntimeError, match="already registered"):
            mount_static(app)

    def test_existing_mount_name_at_wrong_path_fails_explicitly(self) -> None:
        """Test that a misleading mount name cannot suppress static mounting."""
        app = FastAPI()
        app.add_route("/other-static/", lambda: None, name="fastapi-logging-kit-static")

        with pytest.raises(RuntimeError, match="unexpected path"):
            mount_static(app)

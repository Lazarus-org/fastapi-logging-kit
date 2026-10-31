import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterator, List

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

import fastapi_logging_kit.settings.checks  # noqa: F401  (populates the check registry)
import fastapi_logging_kit.app as app_module
from fastapi_logging_kit.app import _report_errors, setup_logging
from fastapi_logging_kit.checks import Error
from fastapi_logging_kit.middleware import MonitorLogSizeMiddleware, RequestLogMiddleware
from fastapi_logging_kit.settings import settings_manager
from fastapi_logging_kit.templating import STATIC_URL_PREFIX
from fastapi_logging_kit.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


@pytest.fixture(autouse=True)
def restore_root_logger() -> Iterator[None]:
    """Restore process-wide logging after a test reconfigures it.

    ``setup_logging`` installs handlers on the root logger, so each test
    gets the original level, handlers and logger dictionary back.

    Yields:
        None

    """
    root = logging.getLogger()
    original_level = root.level
    original_handlers = root.handlers.copy()
    original_loggers = root.manager.loggerDict.copy()

    yield

    for handler in root.handlers:
        if handler not in original_handlers:
            handler.close()
    root.handlers.clear()
    root.handlers.extend(original_handlers)
    root.setLevel(original_level)
    root.manager.loggerDict.clear()
    root.manager.loggerDict.update(original_loggers)


@pytest.fixture
def record_set_config(monkeypatch: pytest.MonkeyPatch) -> List[Dict[str, Any]]:
    """Replace ``set_config`` with a recorder so no handlers are installed.

    Args:
        monkeypatch (pytest.MonkeyPatch): The patching helper.

    Returns:
        List[Dict[str, Any]]: The keyword arguments of each call.

    """
    calls: List[Dict[str, Any]] = []

    def recorder(**kwargs: Any) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(app_module, "set_config", recorder)
    return calls


def collect_paths(app: FastAPI) -> List[str]:
    """Return every route path registered on *app*, including nested ones.

    Recent FastAPI versions wrap an included router in a container route,
    so the tree is walked rather than read one level deep.

    Args:
        app (FastAPI): The application to inspect.

    Returns:
        List[str]: Every registered path.

    """
    paths: List[str] = []

    def walk(routes: Any) -> None:
        for route in routes:
            path = getattr(route, "path", None)
            if path is not None:
                paths.append(path)
            included = getattr(route, "original_router", None)
            nested = getattr(included, "routes", None) or getattr(
                route, "routes", None
            )
            if nested:
                walk(nested)

    walk(app.routes)
    return paths


def base_config(tmp_path: Path, **overrides: Any) -> Dict[str, Any]:
    """Return a valid configuration rooted at *tmp_path*.

    Args:
        tmp_path (Path): The directory log files are written to.
        **overrides (Any): Extra configuration keys.

    Returns:
        Dict[str, Any]: The configuration mapping.

    """
    config: Dict[str, Any] = {
        "LOG_DIR": str(tmp_path / "logs"),
        "LOG_FILE_LEVELS": ["INFO", "ERROR"],
        "INITIALIZATION_MESSAGE_ENABLE": False,
    }
    config.update(overrides)
    return config


class TestSetupLoggingWithoutApp:
    """Test suite for `setup_logging` when no application is supplied."""

    def test_applies_the_configuration(
        self, tmp_path: Path, record_set_config: List[Dict[str, Any]]
    ) -> None:
        """Test that the configuration is loaded and handed to set_config.

        Args:
            tmp_path (Path): The temporary log directory root.
            record_set_config (List[Dict[str, Any]]): The recorded calls.

        """
        config = base_config(tmp_path)

        assert setup_logging(config=config) is None

        assert settings_manager.log_dir == config["LOG_DIR"]
        assert len(record_set_config) == 1
        assert record_set_config[0]["log_levels"] == ["INFO", "ERROR"]
        assert record_set_config[0]["log_dir"] == config["LOG_DIR"]

    def test_config_none_keeps_the_existing_configuration(
        self, tmp_path: Path, record_set_config: List[Dict[str, Any]]
    ) -> None:
        """Test that omitting the config leaves the current settings alone.

        Args:
            tmp_path (Path): The temporary log directory root.
            record_set_config (List[Dict[str, Any]]): The recorded calls.

        """
        config = base_config(tmp_path)
        settings_manager.load(config)

        setup_logging()

        assert settings_manager.log_dir == config["LOG_DIR"]
        assert settings_manager.log_levels == ["INFO", "ERROR"]

    def test_creates_the_log_files_end_to_end(self, tmp_path: Path) -> None:
        """Test that a real run creates a log file for every level.

        Args:
            tmp_path (Path): The temporary log directory root.

        """
        setup_logging(config=base_config(tmp_path))

        assert sorted(os.listdir(tmp_path / "logs")) == ["error.log", "info.log"]


class TestConfigurationChecks:
    """Test suite for the configuration validation of `setup_logging`."""

    def test_warns_about_an_invalid_configuration(
        self,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
        record_set_config: List[Dict[str, Any]],
    ) -> None:
        """Test that a failing check is reported as a warning.

        Args:
            tmp_path (Path): The temporary log directory root.
            caplog (pytest.LogCaptureFixture): The log capture fixture.
            record_set_config (List[Dict[str, Any]]): The recorded calls.

        """
        with caplog.at_level(logging.WARNING):
            setup_logging(config=base_config(tmp_path, LOG_FILE_LEVELS=["BOGUS"]))

        assert "[CONFIGURATION ERROR]" in caplog.text
        assert "issue(s) detected" in caplog.text

    def test_valid_configuration_warns_about_nothing(
        self,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
        record_set_config: List[Dict[str, Any]],
    ) -> None:
        """Test that a valid configuration produces no warning.

        Args:
            tmp_path (Path): The temporary log directory root.
            caplog (pytest.LogCaptureFixture): The log capture fixture.
            record_set_config (List[Dict[str, Any]]): The recorded calls.

        """
        with caplog.at_level(logging.WARNING):
            setup_logging(config=base_config(tmp_path))

        assert "[CONFIGURATION ERROR]" not in caplog.text

    def test_checks_can_be_skipped(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        record_set_config: List[Dict[str, Any]],
    ) -> None:
        """Test that ``run_configuration_checks=False`` skips validation.

        Args:
            tmp_path (Path): The temporary log directory root.
            monkeypatch (pytest.MonkeyPatch): The patching helper.
            record_set_config (List[Dict[str, Any]]): The recorded calls.

        """

        def explode(*args: Any, **kwargs: Any) -> None:
            raise AssertionError("checks must not run")

        monkeypatch.setattr(app_module, "run_checks", explode)

        setup_logging(
            config=base_config(tmp_path, LOG_FILE_LEVELS=["BOGUS"]),
            run_configuration_checks=False,
        )

        assert len(record_set_config) == 1


class TestReportErrors:
    """Test suite for the `_report_errors` helper."""

    def test_logs_nothing_without_errors(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that an empty error list produces no output.

        Args:
            caplog (pytest.LogCaptureFixture): The log capture fixture.

        """
        with caplog.at_level(logging.WARNING):
            _report_errors([])

        assert caplog.records == []

    def test_logs_every_error(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test that each error is rendered into the warning.

        Args:
            caplog (pytest.LogCaptureFixture): The log capture fixture.

        """
        errors = [
            Error("first problem", id="fastapi_logging_kit.E001"),
            Error("second problem", hint="fix it", id="fastapi_logging_kit.E002"),
        ]

        with caplog.at_level(logging.WARNING):
            _report_errors(errors)

        assert "2 issue(s) detected" in caplog.text
        assert "first problem" in caplog.text
        assert "HINT: fix it" in caplog.text


class TestMiddlewareInstallation:
    """Test suite for the middleware wiring performed by `setup_logging`."""

    def test_installs_both_middleware(
        self, tmp_path: Path, record_set_config: List[Dict[str, Any]]
    ) -> None:
        """Test that both logging middleware classes are added.

        Args:
            tmp_path (Path): The temporary log directory root.
            record_set_config (List[Dict[str, Any]]): The recorded calls.

        """
        app = FastAPI()
        setup_logging(app, base_config(tmp_path))

        installed = [middleware.cls for middleware in app.user_middleware]
        assert RequestLogMiddleware in installed
        assert MonitorLogSizeMiddleware in installed
        assert installed.index(RequestLogMiddleware) < installed.index(
            MonitorLogSizeMiddleware
        )

    def test_repeated_setup_does_not_duplicate_middleware(
        self, tmp_path: Path, record_set_config: List[Dict[str, Any]]
    ) -> None:
        """Test that calling setup twice keeps one instance of each middleware."""
        app = FastAPI()
        config = base_config(tmp_path)

        setup_logging(app, config)
        setup_logging(app, config)

        installed = [middleware.cls for middleware in app.user_middleware]
        assert installed.count(RequestLogMiddleware) == 1
        assert installed.count(MonitorLogSizeMiddleware) == 1

    def test_partial_middleware_installation_fails_explicitly(
        self, tmp_path: Path, record_set_config: List[Dict[str, Any]]
    ) -> None:
        """Test that a partially pre-installed middleware pair is rejected."""
        app = FastAPI()
        app.add_middleware(RequestLogMiddleware)

        with pytest.raises(RuntimeError, match="partially installed"):
            setup_logging(app, base_config(tmp_path))

    def test_started_app_fails_before_legacy_settings_are_mutated(
        self, tmp_path: Path, record_set_config: List[Dict[str, Any]]
    ) -> None:
        """Test that missing middleware is detected before global configuration changes."""
        app = FastAPI()
        with TestClient(app) as client:
            assert client.get("/not-found").status_code == 404

        original_settings = dict(settings_manager.log_settings)
        with pytest.raises(RuntimeError, match="before the ASGI application starts"):
            setup_logging(app, base_config(tmp_path))

        assert settings_manager.log_settings == original_settings
        assert record_set_config == []

    def test_middleware_can_be_skipped(
        self, tmp_path: Path, record_set_config: List[Dict[str, Any]]
    ) -> None:
        """Test that ``add_middleware=False`` leaves the app untouched.

        Args:
            tmp_path (Path): The temporary log directory root.
            record_set_config (List[Dict[str, Any]]): The recorded calls.

        """
        app = FastAPI()
        setup_logging(app, base_config(tmp_path), add_middleware=False)

        installed = [middleware.cls for middleware in app.user_middleware]
        assert RequestLogMiddleware not in installed
        assert MonitorLogSizeMiddleware not in installed


class TestLogiBoardIntegration:
    """Test suite for the LogiBoard wiring performed by `setup_logging`."""

    def test_includes_the_router_and_static_mount(
        self, tmp_path: Path, record_set_config: List[Dict[str, Any]]
    ) -> None:
        """Test that LogiBoard is wired up when it is enabled.

        Args:
            tmp_path (Path): The temporary log directory root.
            record_set_config (List[Dict[str, Any]]): The recorded calls.

        """
        app = FastAPI()
        setup_logging(
            app,
            base_config(tmp_path, INCLUDE_LOG_iBOARD=True),
            add_middleware=False,
        )

        paths = collect_paths(app)
        assert "/log-iboard/" in paths
        assert STATIC_URL_PREFIX in paths

        with TestClient(app) as client:
            assert client.get("/log-iboard/").status_code == 403
            assert (
                client.get(f"{STATIC_URL_PREFIX}/LogiBoard/css/app.css").status_code
                == 200
            )

    def test_repeated_setup_does_not_duplicate_log_iboard_routes(
        self, tmp_path: Path, record_set_config: List[Dict[str, Any]]
    ) -> None:
        """Test that the dashboard and static mount are installed once."""
        app = FastAPI()
        config = base_config(tmp_path, INCLUDE_LOG_iBOARD=True)

        setup_logging(app, config, add_middleware=False)
        setup_logging(app, config, add_middleware=False)

        paths = collect_paths(app)
        assert paths.count("/log-iboard/") == 1
        assert paths.count(STATIC_URL_PREFIX) == 1

    @pytest.mark.parametrize("prefix", ["", "/admin"])
    def test_included_router_dashboard_conflicts_are_detected(
        self, tmp_path: Path, record_set_config: List[Dict[str, Any]], prefix: str
    ) -> None:
        app = FastAPI()
        router = APIRouter()
        router.add_api_route("/log-iboard/", lambda: None, name="application-dashboard")
        app.include_router(router, prefix=prefix)
        config = base_config(tmp_path, INCLUDE_LOG_iBOARD=True)

        if not prefix:
            with pytest.raises(RuntimeError, match="already registered"):
                setup_logging(app, config, add_middleware=False)
            assert record_set_config == []
        else:
            setup_logging(app, config, add_middleware=False)
            with TestClient(app) as client:
                assert client.get("/log-iboard/").status_code == 403
                assert client.get("/admin/log-iboard/").status_code == 200

    def test_prefixed_dashboard_name_cannot_suppress_installation(
        self, tmp_path: Path, record_set_config: List[Dict[str, Any]]
    ) -> None:
        app = FastAPI()
        router = APIRouter()
        router.add_api_route("/log-iboard/", lambda: None, name="log-iboard")
        app.include_router(router, prefix="/admin")

        with pytest.raises(RuntimeError, match="unexpected path"):
            setup_logging(
                app,
                base_config(tmp_path, INCLUDE_LOG_iBOARD=True),
                add_middleware=False,
            )
        assert record_set_config == []

    def test_structured_setup_respects_legacy_log_iboard_opt_in(self) -> None:
        """Test that structured setup still honors the explicit LogiBoard opt-in."""
        settings_manager.load({"INCLUDE_LOG_iBOARD": True})
        app = FastAPI()

        setup_logging(app, {"COMPONENTS": {}}, add_middleware=False)

        paths = collect_paths(app)
        assert "/log-iboard/" in paths
        assert STATIC_URL_PREFIX in paths

    def test_log_iboard_route_conflict_is_reported(
        self, tmp_path: Path, record_set_config: List[Dict[str, Any]]
    ) -> None:
        """Test that LogiBoard does not silently shadow an application route."""
        app = FastAPI()
        app.add_route("/log-iboard/", lambda: None, name="application-dashboard")

        with pytest.raises(RuntimeError, match="already registered"):
            setup_logging(
                app,
                base_config(tmp_path, INCLUDE_LOG_iBOARD=True),
                add_middleware=False,
            )

    def test_started_app_cannot_enable_log_iboard_after_startup(
        self, tmp_path: Path, record_set_config: List[Dict[str, Any]]
    ) -> None:
        """Test that a late dashboard opt-in fails before loading legacy settings."""
        app = FastAPI()
        with TestClient(app) as client:
            assert client.get("/not-found").status_code == 404

        original_settings = dict(settings_manager.log_settings)
        with pytest.raises(RuntimeError, match="LogiBoard must be enabled before"):
            setup_logging(
                app,
                base_config(tmp_path, INCLUDE_LOG_iBOARD=True),
                add_middleware=False,
            )

        assert settings_manager.log_settings == original_settings
        assert record_set_config == []

    def test_dashboard_named_route_at_wrong_path_fails(
        self, tmp_path: Path, record_set_config: List[Dict[str, Any]]
    ) -> None:
        """Test that a route name alone cannot suppress the LogiBoard router."""
        app = FastAPI()
        app.add_route("/another-dashboard/", lambda: None, name="log-iboard")

        with pytest.raises(RuntimeError, match="unexpected path"):
            setup_logging(
                app,
                base_config(tmp_path, INCLUDE_LOG_iBOARD=True),
                add_middleware=False,
            )

    def test_log_iboard_static_mount_name_at_wrong_path_fails(
        self, tmp_path: Path, record_set_config: List[Dict[str, Any]]
    ) -> None:
        """Test that an unrelated mount name cannot suppress LogiBoard assets."""
        app = FastAPI()
        app.add_route("/another-static/", lambda: None, name="fastapi-logging-kit-static")

        with pytest.raises(RuntimeError, match="unexpected path"):
            setup_logging(
                app,
                base_config(tmp_path, INCLUDE_LOG_iBOARD=True),
                add_middleware=False,
            )

    def test_log_iboard_static_path_conflict_is_reported(
        self, tmp_path: Path, record_set_config: List[Dict[str, Any]]
    ) -> None:
        """Test that LogiBoard cannot replace an application static mount."""
        app = FastAPI()
        app.add_route(STATIC_URL_PREFIX, lambda: None, name="application-static")

        with pytest.raises(RuntimeError, match="already registered"):
            setup_logging(
                app,
                base_config(tmp_path, INCLUDE_LOG_iBOARD=True),
                add_middleware=False,
            )

        assert not app.user_middleware

    def test_excludes_the_router_when_disabled(
        self, tmp_path: Path, record_set_config: List[Dict[str, Any]]
    ) -> None:
        """Test that LogiBoard is absent when it is not enabled.

        Args:
            tmp_path (Path): The temporary log directory root.
            record_set_config (List[Dict[str, Any]]): The recorded calls.

        """
        app = FastAPI()
        setup_logging(
            app,
            base_config(tmp_path, INCLUDE_LOG_iBOARD=False),
            add_middleware=False,
        )

        paths = collect_paths(app)
        assert "/log-iboard/" not in paths
        assert STATIC_URL_PREFIX not in paths

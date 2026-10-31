"""Application integration for ``fastapi_logging_kit``.

``django_logging`` hooked itself into a project through ``AppConfig.ready()``,
which Django calls once the app registry is populated. FastAPI has no such
hook, so integration is explicit: call :func:`setup_logging` once at import
time, passing your ``FastAPI`` instance to also install the middleware and
the LogiBoard router.

    from fastapi import FastAPI
    from fastapi_logging_kit import setup_logging

    app = FastAPI()
    setup_logging(app, {"LOG_DIR": "logs", "LOG_FILE_LEVELS": ["INFO", "ERROR"]})

Calling it without an application configures only the logging itself,
which is what the CLI commands and non-web processes need.

"""

import logging
import logging.config
from copy import deepcopy
from threading import RLock
from typing import Any, Iterator, List, Mapping, Optional

from fastapi_logging_kit.checks import Error, run_checks
from fastapi_logging_kit.constants.ansi_colors import AnsiColors
from fastapi_logging_kit.settings import settings_manager
from fastapi_logging_kit.utils.get_conf import get_config, include_log_iboard
from fastapi_logging_kit.utils.set_conf import set_config

logger = logging.getLogger(__name__)


def _report_errors(errors: List[Error]) -> None:
    """Log configuration check failures as warnings.

    Django aborts startup when a system check fails. ``fastapi_logging_kit``
    warns instead, so a misconfigured application still boots on the
    default configuration rather than refusing to start.

    Args:
        errors (List[Error]): The errors reported by the checks.

    """
    if not errors:
        return

    colors = AnsiColors()
    logger.warning(
        "\n"
        "========================%sFASTAPI LOGGING KIT%s"
        "========================\n"
        "%s[CONFIGURATION ERROR]%s"
        " %d issue(s) detected in your fastapi_logging_kit configuration:\n%s\n"
        "==============================================================\n",
        colors.RED_BACKGROUND,
        colors.RESET,
        colors.RED,
        colors.RESET,
        len(errors),
        "\n".join(f"  {error}" for error in errors),
    )


# The structured contract is separate from legacy flat-key configuration.
# A per-application marker prevents duplicated ASGI middleware registration.
_STRUCTURED_LOCK = RLock()


def _setup_structured(app: Optional[Any], config: Mapping[str, Any], *, add_middleware: bool) -> None:
    """Apply the approved v1 contract and add request middleware once."""
    from fastapi_logging_kit.settings.contract import compile_settings
    from fastapi_logging_kit.settings.components import compile_components
    from fastapi_logging_kit.settings.activation import activate

    compiled = compile_settings(config)
    if not compiled["ENABLED"]:
        return
    if app is not None and include_log_iboard():
        _validate_log_iboard(app)
    with _STRUCTURED_LOCK:
        if app is not None:
            previous = getattr(app.state, "_fastapi_logging_kit_structured", None)
            if previous is not None:
                if previous != compiled:
                    raise RuntimeError("FastAPI Logging was already configured with different settings")
                return
            if getattr(app, "middleware_stack", None) is not None:
                raise RuntimeError("Configure FastAPI Logging before starting the ASGI application")
        logging_conf = compiled["LOGGING"]
        components = compiled["COMPONENTS"]
        if logging_conf:
            # Explicit LOGGING configuration opts in to the normal, process-wide
            # dictConfig replacement semantics. Disable-existing defaults to False.
            logging_conf.setdefault("disable_existing_loggers", False)
            if components:
                had_root = "root" in logging_conf
                logging_conf = compile_components(logging_conf, components)
                logging_conf = {k: v for k, v in logging_conf.items() if not k.startswith("_fast_")}
                if not had_root and not components.get("root_handlers"):
                    # A missing root section must not silently replace the host root.
                    logging_conf.pop("root", None)
            logging.config.dictConfig(logging_conf)
        else:
            # Without an explicit replacement, all owned handlers are attached
            # additively by the existing transactional component activator.
            preset = {
                "version": 1,
                "formatters": {"console": {"format": "%(levelname)s %(name)s: %(message)s"}},
                "filters": {},
                "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "console", "level": "INFO"}},
                "loggers": {},
                "root": {"handlers": []},
            }
            graph = compile_components(preset, components)
            resolver = logging.config.DictConfigurator({"version": 1}).resolve
            activate(graph, mode="additive", resolver=resolver)
        if app is not None:
            if add_middleware and compiled["REQUEST_LOGGING"]["ENABLED"]:
                from fastapi_logging_kit.middleware import RequestLogMiddleware
                app.add_middleware(RequestLogMiddleware, config=deepcopy(compiled["REQUEST_LOGGING"]))
            if include_log_iboard():
                _install_log_iboard(app)
            app.state._fastapi_logging_kit_structured = compiled


def _iter_app_routes(
    app: Any, prefix: str = ""
) -> Iterator[tuple[Optional[str], Optional[str]]]:
    """Yield route names and effective paths through included routers."""
    for route in getattr(app, "routes", ()):
        path = getattr(route, "path", None)
        yield getattr(route, "name", None), prefix + path if path is not None else None
        included = getattr(route, "original_router", None)
        if included is not None:
            context = getattr(route, "include_context", None)
            yield from _iter_app_routes(included, prefix + getattr(context, "prefix", ""))


def _validate_log_iboard(app: Any) -> None:
    """Detect route conflicts before changing logging or middleware state."""
    from fastapi_logging_kit.templating import STATIC_URL_PREFIX

    for route_name, route_path in _iter_app_routes(app):
        if route_name == "log-iboard" and route_path != "/log-iboard/":
            raise RuntimeError(
                "The route named 'log-iboard' is registered at an "
                f"unexpected path: {route_path!r}."
            )
        if route_name != "log-iboard" and route_path == "/log-iboard/":
            raise RuntimeError(
                "Cannot install LogiBoard: '/log-iboard/' is already registered."
            )
        if route_name == "fastapi-logging-kit-static" and route_path != STATIC_URL_PREFIX:
            raise RuntimeError(
                "The route named 'fastapi-logging-kit-static' is registered at an "
                f"unexpected path: {route_path!r}."
            )
        if route_name != "fastapi-logging-kit-static" and route_path == STATIC_URL_PREFIX:
            raise RuntimeError(
                f"Cannot mount LogiBoard assets: {STATIC_URL_PREFIX!r} "
                "is already registered by another route."
            )


def _validate_legacy_app_setup(
    app: Any, *, add_middleware: bool, include_dashboard: bool
) -> None:
    """Preflight legacy ASGI changes before mutating process-wide settings."""
    installed = {middleware.cls for middleware in app.user_middleware}
    expected = set()
    if add_middleware:
        from fastapi_logging_kit.middleware import (
            MonitorLogSizeMiddleware,
            RequestLogMiddleware,
        )

        expected = {MonitorLogSizeMiddleware, RequestLogMiddleware}
        present = installed & expected
        if present and present != expected:
            raise RuntimeError(
                "FastAPI Logging Kit middleware is partially installed; configure it "
                "once before serving requests."
            )
        if app.middleware_stack is not None and present != expected:
            raise RuntimeError(
                "FastAPI Logging Kit middleware must be configured before the ASGI "
                "application starts serving requests."
            )

    if include_dashboard:
        _validate_log_iboard(app)
        if app.middleware_stack is not None:
            route_names = {name for name, _ in _iter_app_routes(app)}
            if not {"log-iboard", "fastapi-logging-kit-static"}.issubset(route_names):
                raise RuntimeError(
                    "LogiBoard must be enabled before the ASGI application "
                    "starts serving requests."
                )


def _install_log_iboard(app: Any) -> None:
    """Install the LogiBoard route and static mount without duplicates."""
    from fastapi_logging_kit.routers import log_iboard as log_iboard_router
    from fastapi_logging_kit.routers import router

    _validate_log_iboard(app)
    has_dashboard = any(
        name == "log-iboard" for name, _ in _iter_app_routes(app)
    )
    if not has_dashboard:
        app.include_router(router)
    log_iboard_router.mount_static(app)


def setup_logging(
    app: Optional[Any] = None,
    config: Optional[Mapping[str, Any]] = None,
    *,
    add_middleware: bool = True,
    run_configuration_checks: bool = True,
) -> None:
    """Configure ``fastapi_logging_kit`` and wire it into a FastAPI application.

    This is the ``fastapi_logging_kit`` replacement for ``AppConfig.ready()``. It
    resolves the configuration, validates it, applies the logging setup
    and — when an application is supplied — installs the request logging
    middleware and the LogiBoard router.

    Args:
        app (Optional[Any]): The FastAPI application to wire into. When
            omitted, only the logging configuration is applied.
        config (Optional[Mapping[str, Any]]): The configuration mapping.
            When omitted, the structured defaults are used unless legacy
            flat-key settings have already been loaded.
        add_middleware (bool): Whether to install request middleware.
            The legacy flat-key path also installs MonitorLogSizeMiddleware;
            the structured contract installs RequestLogMiddleware only.
        run_configuration_checks (bool): Whether to validate the
            configuration and warn about any problems.

    """
    if config is None and not settings_manager.log_settings:
        _setup_structured(app, {}, add_middleware=add_middleware)
        return

    if config is not None and (
        "ENABLED" in config or "LOGGING" in config
        or "COMPONENTS" in config or "REQUEST_LOGGING" in config
    ):
        _setup_structured(app, config, add_middleware=add_middleware)
        return

    if app is not None:
        from fastapi_logging_kit.settings.manager import SettingsManager

        intended_settings = (
            SettingsManager(config) if config is not None else settings_manager
        )
        _validate_legacy_app_setup(
            app,
            add_middleware=add_middleware,
            include_dashboard=intended_settings.include_log_iboard,
        )

    if config is not None:
        settings_manager.load(config)

    if run_configuration_checks:
        # Importing the module is what registers the checks, via the
        # @register() decorators applied at import time. Django got this for
        # free by importing every app's checks module through the app
        # registry; here it has to be explicit, and without it the registry
        # would be empty and run_checks would report nothing.
        import fastapi_logging_kit.settings.checks  # noqa: F401  pylint: disable=unused-import

        _report_errors(run_checks(None))

    # Apply the logging configuration
    set_config(**get_config())

    if app is None:
        return

    if add_middleware:
        from fastapi_logging_kit.middleware import (
            MonitorLogSizeMiddleware,
            RequestLogMiddleware,
        )

        installed = {middleware.cls for middleware in app.user_middleware}
        expected = {MonitorLogSizeMiddleware, RequestLogMiddleware}
        if not expected.issubset(installed):
            # Added in reverse order: add_middleware prepends, so the request
            # logger ends up outermost and times the full request.
            app.add_middleware(MonitorLogSizeMiddleware)
            app.add_middleware(RequestLogMiddleware)

    if include_log_iboard():
        _install_log_iboard(app)

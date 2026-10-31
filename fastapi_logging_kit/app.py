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
from typing import Any, List, Mapping, Optional

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
            app.state._fastapi_logging_kit_structured = compiled


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
            When omitted, the existing configuration (from environment
            variables and defaults) is kept.
        add_middleware (bool): Whether to install RequestLogMiddleware
            and MonitorLogSizeMiddleware on *app*.
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

        # Added in reverse order: add_middleware prepends, so the request
        # logger ends up outermost and times the full request.
        app.add_middleware(MonitorLogSizeMiddleware)
        app.add_middleware(RequestLogMiddleware)

    if include_log_iboard():
        from fastapi_logging_kit.routers import log_iboard as log_iboard_router
        from fastapi_logging_kit.routers import router

        app.include_router(router)
        log_iboard_router.mount_static(app)

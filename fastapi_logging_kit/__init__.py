"""fastapi_logging_kit — logging for FastAPI applications.

A port of ``django_logging`` that extends Python's built-in ``logging`` without relying
on any third-party logging library, providing per-level log files, JSON/XML/FLAT output
formats, colourised console output, request logging middleware, context variables, log
rotation, email notifications and a maintenance CLI.
"""

from fastapi_logging_kit.app import setup_logging
from fastapi_logging_kit.cache import set_cache
from fastapi_logging_kit.contextvar import manager
from fastapi_logging_kit.decorators import execution_tracker
from fastapi_logging_kit.filters import ContextVarFilter, LoggingLevelFilter
from fastapi_logging_kit.formatters import (
    ColoredFormatter,
    FLATFormatter,
    JSONFormatter,
    XMLFormatter,
)
from fastapi_logging_kit.handlers import (
    CompressedRotatingFileHandler,
    CompressedTimedRotatingFileHandler,
    EmailHandler,
)
from fastapi_logging_kit.middleware import (
    MonitorLogSizeMiddleware,
    RequestLogMiddleware,
)
from fastapi_logging_kit.settings import settings_manager
from fastapi_logging_kit.utils.context_manager import config_setup
from fastapi_logging_kit.utils.log_email_notifier.log_and_notify import (
    log_and_notify_admin,
)
from fastapi_logging_kit.utils.sql import instrument_sqlalchemy, record_query

__version__ = "1.0.0"

__all__ = [
    "ColoredFormatter",
    "CompressedRotatingFileHandler",
    "CompressedTimedRotatingFileHandler",
    "ContextVarFilter",
    "EmailHandler",
    "FLATFormatter",
    "JSONFormatter",
    "LoggingLevelFilter",
    "MonitorLogSizeMiddleware",
    "RequestLogMiddleware",
    "XMLFormatter",
    "__version__",
    "config_setup",
    "execution_tracker",
    "instrument_sqlalchemy",
    "log_and_notify_admin",
    "manager",
    "record_query",
    "set_cache",
    "settings_manager",
    "setup_logging",
]

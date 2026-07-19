"""fast_logging — logging for FastAPI applications.

A port of ``django_logging`` that extends Python's built-in ``logging``
without relying on any third-party logging library, providing per-level
log files, JSON/XML/FLAT output formats, colourised console output,
request logging middleware, context variables, log rotation, email
notifications and a maintenance CLI.

"""

from fast_logging.app import setup_logging
from fast_logging.cache import set_cache
from fast_logging.contextvar import manager
from fast_logging.decorators import execution_tracker
from fast_logging.filters import ContextVarFilter, LoggingLevelFilter
from fast_logging.formatters import (
    ColoredFormatter,
    FLATFormatter,
    JSONFormatter,
    XMLFormatter,
)
from fast_logging.handlers import (
    CompressedRotatingFileHandler,
    CompressedTimedRotatingFileHandler,
    EmailHandler,
)
from fast_logging.middleware import MonitorLogSizeMiddleware, RequestLogMiddleware
from fast_logging.settings import settings_manager
from fast_logging.utils.context_manager import config_setup
from fast_logging.utils.log_email_notifier.log_and_notify import log_and_notify_admin
from fast_logging.utils.sql import instrument_sqlalchemy, record_query

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

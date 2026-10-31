"""Execution-time and optional database-query diagnostics."""

import inspect
import logging
import os
from contextlib import nullcontext
from functools import wraps
from time import perf_counter
from typing import Any, Callable, ContextManager, Optional

from fastapi_logging_kit.utils.get_conf import is_debug_enabled
from fastapi_logging_kit.utils.sql import (
    get_queries,
    query_capture,
    query_capture_active,
)
from fastapi_logging_kit.utils.time import format_elapsed_time
from fastapi_logging_kit.validators.config_validators import (
    validate_boolean_setting,
    validate_integer_setting,
)

logger = logging.getLogger(__name__)


def execution_tracker(
    logging_level: int = logging.INFO,
    log_queries: bool = False,
    query_threshold: Optional[int] = None,
    query_exceed_warning: bool = False,
) -> Callable:
    """Log function duration and optionally count SQL statements.

    Both synchronous and asynchronous functions are supported. Query history
    is never cleared: the decorator counts only statements recorded during
    the decorated call, preserving any enclosing request-level capture scope.
    When used outside a request scope, query capture is isolated and bounded.
    """
    errors = []
    errors.extend(
        validate_integer_setting(logging_level, "execution_tracker.logging_level")
    )
    errors.extend(
        validate_boolean_setting(log_queries, "execution_tracker.log_queries")
    )
    if query_threshold is not None:
        errors.extend(
            validate_integer_setting(
                query_threshold, "execution_tracker.query_threshold"
            )
        )
    errors.extend(
        validate_boolean_setting(
            query_exceed_warning, "execution_tracker.query_exceed_warning"
        )
    )
    if errors:
        raise ValueError(errors[0])

    def decorator(func: Callable) -> Callable:
        is_async = inspect.iscoroutinefunction(func)

        def log_success(started: float, count: Optional[int], debug: bool) -> None:
            function_name = func.__qualname__
            exceeded = (
                count is not None
                and query_threshold is not None
                and count > query_threshold
            )
            if exceeded and query_exceed_warning:
                logger.warning(
                    "Number of database queries (%s) exceeded threshold (%s) "
                    "for function '%s'",
                    count,
                    query_threshold,
                    function_name,
                )
            elif log_queries and not debug:
                logger.warning(
                    "DEBUG mode is disabled, so database queries are not tracked. "
                    "To include number of queries, set DEBUG to True in your "
                    "fastapi_logging_kit configuration."
                )

            if not logger.isEnabledFor(logging_level):
                return
            message = (
                f"Performance Metrics for Function: '{function_name}'\\n"
                f"  Module: {func.__module__}\\n"
                f"  File: {os.path.abspath(func.__code__.co_filename)}, "
                f"Line: {func.__code__.co_firstlineno}\\n"
                f"  Execution Time: {format_elapsed_time(perf_counter() - started)}"
            )
            if count is not None:
                message += f"\\n  Database Queries: {count} queries "
                if exceeded:
                    message += f"(exceeds threshold of ({query_threshold}))"
            logger.log(logging_level, message)

        def log_failure(exc: Exception) -> None:
            logger.error(
                "Error executing function '%s': %s",
                func.__qualname__,
                str(exc),
                exc_info=True,
            )

        def capture_scope(debug: bool) -> ContextManager[Any]:
            if not (debug and log_queries) or query_capture_active():
                return nullcontext()
            return query_capture(max_bytes=4096, max_queries=100)

        if is_async:

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                started = perf_counter()
                debug = is_debug_enabled()
                with capture_scope(debug):
                    before = len(get_queries()) if debug and log_queries else 0
                    try:
                        result = await func(*args, **kwargs)
                    except Exception as exc:
                        log_failure(exc)
                        raise
                    count = (
                        len(get_queries()) - before if debug and log_queries else None
                    )
                    log_success(started, count, debug)
                    return result

            return async_wrapper

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            started = perf_counter()
            debug = is_debug_enabled()
            with capture_scope(debug):
                before = len(get_queries()) if debug and log_queries else 0
                try:
                    result = func(*args, **kwargs)
                except Exception as exc:
                    log_failure(exc)
                    raise
                count = len(get_queries()) - before if debug and log_queries else None
                log_success(started, count, debug)
                return result

        return wrapper

    return decorator

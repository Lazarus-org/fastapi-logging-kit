"""Bounded, context-local SQL query diagnostics.

FastAPI does not prescribe a database layer. Applications can use
:func:`record_query` from their own instrumentation or install the
optional SQLAlchemy event integration with
:func:`instrument_sqlalchemy`.

Request and execution scopes use :func:`query_capture` so query history
is isolated, bounded and restored when the scope exits.
"""

from __future__ import annotations

import contextvars
import math
import threading
import time
import weakref
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Dict, Iterator, List, Optional

_queries: contextvars.ContextVar[list[dict[str, str]] | None] = contextvars.ContextVar(
    "_fl_sql_query_log", default=None
)


@dataclass
class _CaptureLimits:
    """Resource limits and status for one query-capture scope."""

    max_bytes: int
    max_queries: int
    used_bytes: int = 0
    truncated: bool = False


_capture_limits: contextvars.ContextVar[_CaptureLimits | None] = contextvars.ContextVar(
    "_fl_sql_capture_limits", default=None
)
_implicit_limits: contextvars.ContextVar[_CaptureLimits | None] = (
    contextvars.ContextVar("_fl_sql_implicit_limits", default=None)
)
_DEFAULT_MAX_BYTES = 65_536
_DEFAULT_MAX_QUERIES = 1_000


def get_queries() -> list[dict[str, str]]:
    """Return the query list associated with the current execution context."""
    queries = _queries.get()
    if queries is None:
        queries = []
        _queries.set(queries)
    return queries


def record_query(sql: str, duration: float) -> None:
    """Record a query, respecting the active capture scope's resource limits.

    Calls made outside :func:`query_capture` use a bounded context-local default
    history. Request middleware and execution tracking use explicit isolated scopes with
    their own configurable limits.
    """
    if not isinstance(sql, str):
        raise TypeError("sql must be a string")
    if isinstance(duration, bool):
        raise TypeError("duration must be a finite non-negative number")
    try:
        elapsed = float(duration)
    except (TypeError, ValueError, OverflowError) as exc:
        raise TypeError("duration must be a finite non-negative number") from exc
    if not math.isfinite(elapsed) or elapsed < 0:
        raise ValueError("duration must be a finite non-negative number")

    formatted_time = f"{elapsed:.3f}"
    limits = _capture_limits.get()
    if limits is None:
        limits = _implicit_limits.get()
        if limits is None:
            limits = _CaptureLimits(
                max_bytes=_DEFAULT_MAX_BYTES,
                max_queries=_DEFAULT_MAX_QUERIES,
            )
            _implicit_limits.set(limits)
    if limits.truncated:
        return
    # Avoid allocating an encoded copy of an arbitrarily large SQL string.
    if len(sql) > limits.max_bytes:
        limits.truncated = True
        return
    sql_size = len(sql.encode("utf-8", errors="replace"))
    entry_size = sql_size + len(formatted_time) + 24
    queries = get_queries()
    if (
        len(queries) >= limits.max_queries
        or limits.used_bytes + entry_size > limits.max_bytes
    ):
        limits.truncated = True
        return
    limits.used_bytes += entry_size
    queries.append({"time": formatted_time, "sql": sql})


def clear_queries() -> None:
    """Discard query history and reset its implicit resource budget.

    Prefer :func:`query_capture` for request and task scopes because it also restores
    the previous context on exit.
    """
    _queries.set([])
    limits = _capture_limits.get()
    if limits is not None:
        limits.used_bytes = 0
        limits.truncated = False
    implicit = _implicit_limits.get()
    if implicit is not None:
        implicit.used_bytes = 0
        implicit.truncated = False


@contextmanager
def query_capture(
    *, max_bytes: int = 4096, max_queries: int = 100
) -> Iterator[list[dict[str, str]]]:
    """Create an isolated bounded query-capture scope.

    Nested scopes are safe: exiting restores the caller's previous query
    history and capture policy. A query that would exceed either limit is
    not retained and marks the capture as truncated.
    """
    # pylint: disable=unidiomatic-typecheck
    if type(max_bytes) is not int or max_bytes < 0:
        raise ValueError("max_bytes must be a non-negative integer")
    if type(max_queries) is not int or max_queries < 1:
        raise ValueError("max_queries must be a positive integer")
    queries_token = _queries.set([])
    limits = _CaptureLimits(max_bytes=max_bytes, max_queries=max_queries)
    limits_token = _capture_limits.set(limits)
    try:
        yield get_queries()
    finally:
        _capture_limits.reset(limits_token)
        _queries.reset(queries_token)


def query_capture_active() -> bool:
    """Return whether the current context already owns a bounded query scope."""
    return _capture_limits.get() is not None


def query_capture_truncated() -> bool:
    """Return whether the active capture scope reached a configured limit."""
    limits = _capture_limits.get()
    return bool(limits and limits.truncated)


def instrument_sqlalchemy(engine: Any) -> None:
    """Instrument a SQLAlchemy Engine or AsyncEngine exactly once.

    SQLAlchemy is an optional dependency. AsyncEngine is supported through its
    synchronous event target. Failed statements are recorded as well as successful
    statements.
    """
    from sqlalchemy import event  # pylint: disable=import-outside-toplevel

    target = getattr(engine, "sync_engine", engine)
    with _instrument_lock:
        if target in _instrumented_engines:
            return

        def before_execute(
            conn: Any, cursor: Any, statement: str, *args: Any, **kwargs: Any
        ) -> None:
            conn.info.setdefault("_fastapi_logging_kit_query_start", []).append(
                time.perf_counter()
            )

        def pop_start(conn: Any) -> float:
            started = conn.info.get("_fastapi_logging_kit_query_start")
            if not started:
                return 0.0
            return max(0.0, time.perf_counter() - started.pop())

        def after_execute(
            conn: Any, cursor: Any, statement: str, *args: Any, **kwargs: Any
        ) -> None:
            record_query(statement, pop_start(conn))

        def handle_error(exception_context: Any) -> None:
            connection = getattr(exception_context, "connection", None)
            statement = getattr(exception_context, "statement", None)
            if connection is not None:
                duration = pop_start(connection)
                if isinstance(statement, str):
                    record_query(statement, duration)

        event.listen(target, "before_cursor_execute", before_execute)
        event.listen(target, "after_cursor_execute", after_execute)
        event.listen(target, "handle_error", handle_error)
        _instrumented_engines.add(target)


_instrumented_engines: weakref.WeakSet[Any] = weakref.WeakSet()
_instrument_lock = threading.RLock()

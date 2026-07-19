"""SQL query tracking for request and execution logging.

``django_logging`` counted queries by reading ``connection.queries``,
which Django populates automatically while ``DEBUG`` is on. FastAPI ships
no ORM, so ``fast_logging`` keeps an equivalent per-context query log of
its own and offers an opt-in SQLAlchemy instrumentation that fills it.

Applications using another database library can call :func:`record_query`
directly from their own instrumentation.

"""

import contextvars
import time
from typing import Any, Dict, List, Optional

# The queries recorded for the current context (request, task or thread).
#
# The name deliberately avoids the "fast_logging_" prefix that
# ContextVarManager uses to namespace log context: anything carrying that
# prefix is merged into every LogRecord's "context" attribute, and the raw
# query log has no business appearing there.
_queries: contextvars.ContextVar[Optional[List[Dict[str, str]]]] = contextvars.ContextVar(
    "_fl_sql_query_log", default=None
)


def get_queries() -> List[Dict[str, str]]:
    """Return the queries recorded in the current context.

    Returns:
        List[Dict[str, str]]: Query dicts with ``time`` and ``sql`` keys,
        matching the shape of Django's ``connection.queries``.

    """
    queries = _queries.get()
    if queries is None:
        queries = []
        _queries.set(queries)
    return queries


def record_query(sql: str, duration: float) -> None:
    """Record a single executed query in the current context.

    Args:
        sql (str): The SQL statement that was executed.
        duration (float): How long it took, in seconds.

    """
    get_queries().append({"time": f"{duration:.3f}", "sql": sql})


def clear_queries() -> None:
    """Discard every query recorded in the current context."""
    _queries.set([])


def instrument_sqlalchemy(engine: Any) -> None:
    """Record every statement executed by a SQLAlchemy engine.

    This is the ``fast_logging`` replacement for Django's automatic
    query capture. Call it once at startup with your ``Engine`` (or
    ``AsyncEngine``) and enable ``LOG_SQL_QUERIES_ENABLE`` to have the
    request middleware report the queries each request issued.

    Args:
        engine (Any): A SQLAlchemy ``Engine``, ``AsyncEngine`` or any
            object exposing a ``sync_engine``.

    Raises:
        ImportError: If SQLAlchemy is not installed.

    """
    from sqlalchemy import event  # pylint: disable=import-outside-toplevel

    target = getattr(engine, "sync_engine", engine)

    def before_execute(
        conn: Any, cursor: Any, statement: str, *args: Any, **kwargs: Any
    ) -> None:
        conn.info.setdefault("_fast_logging_query_start", []).append(time.perf_counter())

    def after_execute(
        conn: Any, cursor: Any, statement: str, *args: Any, **kwargs: Any
    ) -> None:
        started = conn.info.get("_fast_logging_query_start")
        elapsed = time.perf_counter() - started.pop(-1) if started else 0.0
        record_query(statement, elapsed)

    event.listen(target, "before_cursor_execute", before_execute)
    event.listen(target, "after_cursor_execute", after_execute)

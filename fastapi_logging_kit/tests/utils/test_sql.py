import sys
import threading
from typing import Any, Dict

import pytest

from fastapi_logging_kit.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON
from fastapi_logging_kit.utils.sql import (
    clear_queries,
    get_queries,
    instrument_sqlalchemy,
    record_query,
)

pytestmark = [
    pytest.mark.utils,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


class TestQueryLog:
    """Test suite for the per-context SQL query log."""

    def test_get_queries_initializes_empty_list(self) -> None:
        """Test that `get_queries` seeds and reuses an empty list.

        A fresh thread starts with an empty context, so the contextvar
        still holds its ``None`` default and the lazy initialization
        branch is exercised.
        """
        captured: Dict[str, Any] = {}

        def collect() -> None:
            """Read the query log twice from a pristine context."""
            captured["first"] = get_queries()
            captured["second"] = get_queries()

        thread = threading.Thread(target=collect)
        thread.start()
        thread.join()

        assert captured["first"] == []
        assert captured["second"] is captured["first"]

    def test_get_queries_reuses_the_existing_list(self) -> None:
        """Test that repeated calls return the same list object."""
        queries = get_queries()

        assert queries == []
        assert get_queries() is queries

    def test_record_query_appends_formatted_entry(self) -> None:
        """Test that `record_query` stores the statement and elapsed time."""
        record_query("SELECT * FROM users", 0.123456)

        queries = get_queries()

        assert len(queries) == 1
        assert queries[0] == {"time": "0.123", "sql": "SELECT * FROM users"}

    def test_record_query_appends_in_order(self) -> None:
        """Test that repeated recordings accumulate in call order."""
        record_query("SELECT 1", 0.001)
        record_query("SELECT 2", 0.002)

        assert [query["sql"] for query in get_queries()] == ["SELECT 1", "SELECT 2"]

    def test_clear_queries_empties_the_log(self) -> None:
        """Test that `clear_queries` discards every recorded query."""
        record_query("SELECT 1", 0.5)
        assert get_queries()

        clear_queries()

        assert get_queries() == []


class TestInstrumentSqlalchemy:
    """Test suite for the `instrument_sqlalchemy` helper."""

    def test_records_executed_statement(self) -> None:
        """Test that a statement run on an instrumented engine is recorded."""
        from sqlalchemy import create_engine, text

        engine = create_engine("sqlite://")
        instrument_sqlalchemy(engine)
        clear_queries()

        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        queries = get_queries()

        assert len(queries) == 1
        assert "SELECT 1" in queries[0]["sql"]
        assert float(queries[0]["time"]) >= 0.0

    def test_instruments_sync_engine_attribute(self) -> None:
        """Test that an `AsyncEngine`-style wrapper is unwrapped."""
        from sqlalchemy import create_engine, text

        engine = create_engine("sqlite://")

        class _AsyncEngineLike:
            """A stand-in for SQLAlchemy's `AsyncEngine`."""

            def __init__(self, sync_engine: Any) -> None:
                """Store the wrapped synchronous engine."""
                self.sync_engine = sync_engine

        instrument_sqlalchemy(_AsyncEngineLike(engine))
        clear_queries()

        with engine.connect() as connection:
            connection.execute(text("SELECT 2"))

        queries = get_queries()

        assert len(queries) == 1
        assert "SELECT 2" in queries[0]["sql"]

    def test_records_zero_elapsed_when_start_stack_is_empty(self) -> None:
        """Test that a missing start time yields a zero elapsed duration."""
        from sqlalchemy import create_engine, event, text

        engine = create_engine("sqlite://")
        instrument_sqlalchemy(engine)

        def drain_start_times(
            conn: Any, cursor: Any, statement: str, *args: Any, **kwargs: Any
        ) -> None:
            """Empty the start-time stack before the statement completes."""
            conn.info["_fastapi_logging_kit_query_start"] = []

        event.listen(engine, "before_cursor_execute", drain_start_times)
        clear_queries()

        with engine.connect() as connection:
            connection.execute(text("SELECT 3"))

        queries = get_queries()

        assert len(queries) == 1
        assert queries[0]["time"] == "0.000"

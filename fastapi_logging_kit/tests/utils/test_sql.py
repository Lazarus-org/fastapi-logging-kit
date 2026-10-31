import asyncio
import sys
import threading
from typing import Any, Dict

import pytest

from fastapi_logging_kit.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON
from fastapi_logging_kit.utils.sql import (
    clear_queries,
    get_queries,
    instrument_sqlalchemy,
    query_capture,
    query_capture_active,
    query_capture_truncated,
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
        engine.dispose()

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
        engine.dispose()

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
        engine.dispose()


class TestBoundedQueryCapture:
    """Tests for isolated and bounded query-capture scopes."""

    def test_scope_is_bounded_by_query_count_and_restores_outer_history(self) -> None:
        record_query("SELECT outer", 0.01)
        outer = get_queries()
        with query_capture(max_bytes=4096, max_queries=1) as captured:
            assert query_capture_active() is True
            record_query("SELECT first", 0.01)
            record_query("SELECT second", 0.02)
            assert len(captured) == 1
            assert query_capture_truncated() is True
            record_query("SELECT ignored after truncation", 0.03)
            assert len(captured) == 1
        assert query_capture_active() is False
        assert get_queries() is outer
        assert [item["sql"] for item in outer] == ["SELECT outer"]

    def test_scope_is_bounded_by_encoded_bytes(self) -> None:
        with query_capture(max_bytes=8, max_queries=10):
            record_query("SELECT 123456789", 0.01)
            assert get_queries() == []
            assert query_capture_truncated() is True

    def test_nested_scope_restores_parent_capture(self) -> None:
        with query_capture(max_bytes=4096):
            record_query("SELECT parent", 0.01)
            parent = get_queries()
            with query_capture(max_bytes=4096):
                record_query("SELECT child", 0.01)
                assert get_queries()[0]["sql"] == "SELECT child"
            assert get_queries() is parent
            assert [item["sql"] for item in get_queries()] == ["SELECT parent"]

    def test_zero_byte_scope_records_no_query(self) -> None:
        with query_capture(max_bytes=0):
            record_query("SELECT 1", 0.01)
            assert get_queries() == []
            assert query_capture_truncated() is True
            clear_queries()
            assert query_capture_truncated() is False
            record_query("SELECT 2", 0.01)
            assert get_queries() == []

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"max_bytes": -1},
            {"max_bytes": True},
            {"max_queries": 0},
            {"max_queries": True},
        ],
    )
    def test_rejects_invalid_scope_limits(self, kwargs: Dict[str, Any]) -> None:
        with pytest.raises(ValueError):
            with query_capture(**kwargs):
                pass

    def test_rejects_invalid_query_values(self) -> None:
        with pytest.raises(TypeError, match="sql must be a string"):
            record_query(123, 0.01)  # type: ignore[arg-type]
        with pytest.raises(TypeError, match="duration"):
            record_query("SELECT 1", "fast")  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="finite"):
            record_query("SELECT 1", float("nan"))
        with pytest.raises(ValueError, match="finite"):
            record_query("SELECT 1", -0.1)

    def test_records_after_scope_exit_in_restored_context(self) -> None:
        with query_capture(max_bytes=4096):
            record_query("SELECT scoped", 0.01)
        record_query("SELECT restored", 0.02)
        assert [item["sql"] for item in get_queries()] == ["SELECT restored"]


class TestSQLAlchemyInstrumentationSafety:
    """Tests for idempotent instrumentation and failed statements."""

    def test_repeated_instrumentation_does_not_duplicate_events(self) -> None:
        from sqlalchemy import create_engine, text

        engine = create_engine("sqlite://")
        instrument_sqlalchemy(engine)
        instrument_sqlalchemy(engine)
        with query_capture(max_bytes=4096):
            with engine.connect() as connection:
                connection.execute(text("SELECT 42"))
            assert len(get_queries()) == 1
        engine.dispose()

    def test_failed_statement_is_recorded(self) -> None:
        from sqlalchemy import create_engine, text
        from sqlalchemy.exc import OperationalError

        engine = create_engine("sqlite://")
        instrument_sqlalchemy(engine)
        with query_capture(max_bytes=4096):
            with engine.connect() as connection:
                with pytest.raises(OperationalError):
                    connection.execute(text("SELECT * FROM missing_table"))
            assert len(get_queries()) == 1
            assert "missing_table" in get_queries()[0]["sql"]
        engine.dispose()



class TestImplicitQueryBounds:
    """The public query-recording API is bounded even outside request scopes."""

    def test_default_history_has_a_fixed_query_count_limit(self) -> None:
        for index in range(1_001):
            record_query(f"SELECT {index}", 0.001)
        assert len(get_queries()) == 1_000
        clear_queries()
        record_query("SELECT after clear", 0.001)
        assert [query["sql"] for query in get_queries()] == ["SELECT after clear"]

    def test_duration_boolean_is_rejected(self) -> None:
        with pytest.raises(TypeError, match="duration"):
            record_query("SELECT 1", True)


class TestConcurrentQueryScopes:
    """Separate async request scopes must never share query history."""

    async def test_parallel_scopes_are_isolated(self) -> None:
        async def capture(statement: str):
            with query_capture(max_bytes=4096):
                await asyncio.sleep(0)
                record_query(statement, 0.01)
                await asyncio.sleep(0)
                return list(get_queries())

        first, second = await asyncio.gather(
            capture("SELECT first"),
            capture("SELECT second"),
        )
        assert [item["sql"] for item in first] == ["SELECT first"]
        assert [item["sql"] for item in second] == ["SELECT second"]

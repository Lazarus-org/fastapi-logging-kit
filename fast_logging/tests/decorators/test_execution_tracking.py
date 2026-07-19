import logging
import sys
from typing import Any

import pytest

from fast_logging.decorators.execution_tracking import execution_tracker
from fast_logging.settings import settings_manager
from fast_logging.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON
from fast_logging.utils.sql import record_query

pytestmark = [
    pytest.mark.decorators,
    pytest.mark.decorators_execution_tracking,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


def _enable_debug() -> None:
    """Turn on the ``DEBUG`` flag of the fast_logging configuration."""
    settings_manager.load({"DEBUG": True})


class TestArgumentValidation:
    """Test suite for the argument validation of `execution_tracker`."""

    def test_rejects_a_non_integer_logging_level(self) -> None:
        """Test that a non-integer logging level is rejected."""
        with pytest.raises(ValueError, match="execution_tracker.logging_level"):
            execution_tracker(logging_level="INFO")

    def test_rejects_a_non_boolean_log_queries(self) -> None:
        """Test that a non-boolean log_queries flag is rejected."""
        with pytest.raises(ValueError, match="execution_tracker.log_queries"):
            execution_tracker(log_queries="yes")

    def test_rejects_an_invalid_query_threshold(self) -> None:
        """Test that a negative query threshold is rejected."""
        with pytest.raises(ValueError, match="execution_tracker.query_threshold"):
            execution_tracker(query_threshold=-1)

    def test_rejects_a_non_boolean_query_exceed_warning(self) -> None:
        """Test that a non-boolean query_exceed_warning flag is rejected."""
        with pytest.raises(ValueError, match="execution_tracker.query_exceed_warning"):
            execution_tracker(query_exceed_warning="no")


class TestExecutionTracking:
    """Test suite for the logging performed by `execution_tracker`."""

    def test_logs_execution_metrics(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test that the happy path logs the performance metrics.

        Args:
            caplog (pytest.LogCaptureFixture): The log capture fixture.

        """

        @execution_tracker()
        def add(first: int, second: int) -> int:
            return first + second

        with caplog.at_level(logging.INFO):
            assert add(2, 3) == 5

        assert "Performance Metrics for Function:" in caplog.text
        assert "<locals>.add'" in caplog.text
        assert "Execution Time:" in caplog.text
        assert "Database Queries" not in caplog.text

    def test_honours_the_requested_logging_level(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that the metrics are logged at the configured level.

        Args:
            caplog (pytest.LogCaptureFixture): The log capture fixture.

        """

        @execution_tracker(logging_level=logging.DEBUG)
        def noop() -> None:
            return None

        with caplog.at_level(logging.DEBUG):
            noop()

        assert caplog.records[-1].levelno == logging.DEBUG

    def test_preserves_the_wrapped_function_metadata(self) -> None:
        """Test that ``functools.wraps`` keeps the original function identity."""

        @execution_tracker()
        def documented() -> None:
            """Original docstring."""

        assert documented.__name__ == "documented"
        assert documented.__doc__ == "Original docstring."

    def test_logs_and_reraises_an_exception(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that a failing function is logged and the error re-raised.

        Args:
            caplog (pytest.LogCaptureFixture): The log capture fixture.

        """

        @execution_tracker()
        def failing() -> None:
            raise RuntimeError("boom")

        with caplog.at_level(logging.ERROR):
            with pytest.raises(RuntimeError, match="boom"):
                failing()

        assert "Error executing function" in caplog.text
        assert "<locals>.failing': boom" in caplog.text


class TestQueryTracking:
    """Test suite for the query counting of `execution_tracker`."""

    def test_includes_the_query_count_when_debug_is_enabled(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that the number of queries is reported in debug mode.

        Args:
            caplog (pytest.LogCaptureFixture): The log capture fixture.

        """
        _enable_debug()

        @execution_tracker(log_queries=True)
        def query_twice() -> None:
            record_query("SELECT 1", 0.01)
            record_query("SELECT 2", 0.02)

        with caplog.at_level(logging.INFO):
            query_twice()

        assert "Database Queries: 2 queries" in caplog.text
        assert "exceeds threshold" not in caplog.text

    def test_reports_a_threshold_breach_with_a_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that exceeding the threshold logs an extra warning.

        Args:
            caplog (pytest.LogCaptureFixture): The log capture fixture.

        """
        _enable_debug()

        @execution_tracker(
            log_queries=True, query_threshold=1, query_exceed_warning=True
        )
        def query_twice() -> None:
            record_query("SELECT 1", 0.01)
            record_query("SELECT 2", 0.02)

        with caplog.at_level(logging.INFO):
            query_twice()

        assert "exceeds threshold of (1)" in caplog.text
        assert any(
            record.levelno == logging.WARNING
            and "exceeded threshold" in record.getMessage()
            for record in caplog.records
        )

    def test_reports_a_threshold_breach_without_a_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that the extra warning is suppressed when not requested.

        Args:
            caplog (pytest.LogCaptureFixture): The log capture fixture.

        """
        _enable_debug()

        @execution_tracker(
            log_queries=True, query_threshold=1, query_exceed_warning=False
        )
        def query_twice() -> None:
            record_query("SELECT 1", 0.01)
            record_query("SELECT 2", 0.02)

        with caplog.at_level(logging.INFO):
            query_twice()

        assert "exceeds threshold of (1)" in caplog.text
        assert not any(
            record.levelno == logging.WARNING for record in caplog.records
        )

    def test_stays_below_the_threshold(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that no breach is reported when the threshold is respected.

        Args:
            caplog (pytest.LogCaptureFixture): The log capture fixture.

        """
        _enable_debug()

        @execution_tracker(
            log_queries=True, query_threshold=5, query_exceed_warning=True
        )
        def query_once() -> None:
            record_query("SELECT 1", 0.01)

        with caplog.at_level(logging.INFO):
            query_once()

        assert "Database Queries: 1 queries" in caplog.text
        assert "exceeds threshold" not in caplog.text

    def test_warns_when_debug_is_disabled(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that query tracking warns when DEBUG is turned off.

        Args:
            caplog (pytest.LogCaptureFixture): The log capture fixture.

        """

        @execution_tracker(log_queries=True)
        def noop() -> Any:
            return "done"

        with caplog.at_level(logging.INFO):
            assert noop() == "done"

        assert "DEBUG mode is disabled" in caplog.text
        assert "Database Queries" not in caplog.text

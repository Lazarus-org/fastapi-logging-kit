import logging
import sys

import pytest

from fast_logging.contextvar import manager
from fast_logging.filters import ContextVarFilter
from fast_logging.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON

pytestmark = [
    pytest.mark.filters,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


class TestContextVarFilter:
    """Test suite for the `ContextVarFilter` class."""

    def test_uses_ambient_contextvars(
        self, debug_log_record: logging.LogRecord
    ) -> None:
        """Test that a record without a context picks up the bound
        contextvars."""
        manager.bind(request_id="abc-123")

        assert ContextVarFilter().filter(debug_log_record)
        assert debug_log_record.context == {"request_id": "abc-123"}

    def test_bound_context_wins_over_contextvars(
        self, debug_log_record: logging.LogRecord
    ) -> None:
        """Test that a context already on the record takes precedence."""
        manager.bind(request_id="ambient", user="ambient-user")
        debug_log_record.context = {"request_id": "bound"}

        ContextVarFilter().filter(debug_log_record)

        assert debug_log_record.context == {
            "request_id": "bound",
            "user": "ambient-user",
        }

    def test_empty_context_becomes_empty_string(
        self, debug_log_record: logging.LogRecord
    ) -> None:
        """Test that an empty merged context is replaced with an empty
        string."""
        manager.clear()

        assert ContextVarFilter().filter(debug_log_record)
        assert debug_log_record.context == ""

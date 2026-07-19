import logging
import sys

import pytest

from fast_logging.filters import LoggingLevelFilter
from fast_logging.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON

pytestmark = [
    pytest.mark.filters,
    pytest.mark.filters_level_filter,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


class TestLoggingLevelFilter:
    """Test suite for the `LoggingLevelFilter` class."""

    def test_initialization(self) -> None:
        """Test that the filter stores the logging level it was given."""
        filter_instance = LoggingLevelFilter(logging.INFO)
        assert filter_instance.logging_level == logging.INFO

    def test_passes_matching_level(self, debug_log_record: logging.LogRecord) -> None:
        """Test that a record whose level matches is allowed through."""
        debug_log_record.levelno = logging.DEBUG
        assert LoggingLevelFilter(logging.DEBUG).filter(debug_log_record)

    def test_blocks_non_matching_level(
        self, debug_log_record: logging.LogRecord
    ) -> None:
        """Test that a record whose level differs is filtered out."""
        debug_log_record.levelno = logging.WARNING
        assert not LoggingLevelFilter(logging.ERROR).filter(debug_log_record)

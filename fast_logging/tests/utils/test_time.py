import sys

import pytest

from fast_logging.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON
from fast_logging.utils.time import format_elapsed_time

pytestmark = [
    pytest.mark.utils,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


class TestFormatElapsedTime:
    """Test suite for :func:`format_elapsed_time`."""

    def test_sub_minute_duration(self) -> None:
        """Test that a duration under a minute is reported in seconds only."""
        assert format_elapsed_time(12.345) == "12.35 second(s)"

    def test_zero_duration(self) -> None:
        """Test that a zero duration is reported as zero seconds."""
        assert format_elapsed_time(0) == "0.00 second(s)"

    def test_multi_minute_duration(self) -> None:
        """Test that a longer duration is split into minutes and seconds."""
        assert format_elapsed_time(125.5) == "2 minute(s) and 5.50 second(s)"

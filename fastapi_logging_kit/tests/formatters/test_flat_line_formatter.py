import logging
import sys

import pytest

from fastapi_logging_kit.formatters import FLATFormatter
from fastapi_logging_kit.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON

pytestmark = [
    pytest.mark.formatters,
    pytest.mark.flat_formatter,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


class TestFLATFormatterFormat:
    """Test suite for `FLATFormatter.format`."""

    def test_formats_specifiers_as_quoted_pairs(
        self, flat_formatter: FLATFormatter, info_log_record: logging.LogRecord
    ) -> None:
        """Test that each specifier is rendered as `name='value'`."""
        output = flat_formatter.format(info_log_record)
        assert output.startswith("levelname='INFO'")
        assert "message='This is an info message'" in output
        assert "asctime='" in output

    def test_skips_none_values(self, info_log_record: logging.LogRecord) -> None:
        """Test that specifiers resolving to `None` are omitted from the line."""
        formatter = FLATFormatter(fmt="%(levelname)s | %(missing_field)s")
        output = formatter.format(info_log_record)
        assert "missing_field" not in output
        assert output == "levelname='INFO' message='This is an info message'"

    def test_appends_exception_suffix(
        self,
        flat_formatter: FLATFormatter,
        error_with_exc_log_record: logging.LogRecord,
    ) -> None:
        """Test that exception text is appended as an `exception='...'` suffix."""
        output = flat_formatter.format(error_with_exc_log_record)
        assert " exception='" in output
        assert "ValueError: Something went wrong" in output

    def test_omits_exception_suffix_when_absent(
        self, flat_formatter: FLATFormatter, error_log_record: logging.LogRecord
    ) -> None:
        """Test that no exception suffix is added without `exc_info`."""
        assert "exception=" not in flat_formatter.format(error_log_record)

    def test_renders_complex_attribute_value_inline(
        self, info_log_record: logging.LogRecord
    ) -> None:
        """Test that a non-scalar attribute value is stringified into the line."""
        info_log_record.context = {"user": "bob"}
        output = FLATFormatter(fmt="%(context)s").format(info_log_record)
        assert output == 'context=\'{"user":"bob"}\' message=\'This is an info message\''

import logging
import sys

import pytest

from fastapi_logging_kit.formatters.base import BaseStructuredFormatter
from fastapi_logging_kit.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON

pytestmark = [
    pytest.mark.formatters,
    pytest.mark.base_formatter,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


class TestExtractSpecifiers:
    """Test suite for `BaseStructuredFormatter._extract_specifiers`."""

    def test_returns_empty_list_when_fmt_is_none(self) -> None:
        """Test that a `None` format string yields no specifiers."""
        formatter = BaseStructuredFormatter(fmt=None)
        assert formatter.specifiers == []

    def test_extracts_specifiers_from_format_string(self) -> None:
        """Test that every `%(name)s` placeholder is extracted in order."""
        formatter = BaseStructuredFormatter(
            fmt="%(levelname)s | %(asctime)s | %(message)s"
        )
        assert formatter.specifiers == ["levelname", "asctime", "message"]

    def test_extracts_no_specifiers_from_plain_text(self) -> None:
        """Test that text without placeholders yields no specifiers."""
        formatter = BaseStructuredFormatter(fmt="%(message)s")
        assert formatter._extract_specifiers("plain text only") == []


class TestGetFieldValue:
    """Test suite for `BaseStructuredFormatter._get_field_value`."""

    def test_returns_message_for_message_specifier(
        self, info_log_record: logging.LogRecord
    ) -> None:
        """Test that the `message` specifier resolves to the rendered message."""
        formatter = BaseStructuredFormatter(fmt="%(message)s")
        assert (
            formatter._get_field_value(info_log_record, "message")
            == "This is an info message"
        )

    def test_returns_formatted_time_for_asctime_specifier(
        self, info_log_record: logging.LogRecord
    ) -> None:
        """Test that the `asctime` specifier resolves to a formatted timestamp."""
        formatter = BaseStructuredFormatter(fmt="%(asctime)s")
        value = formatter._get_field_value(info_log_record, "asctime")
        assert isinstance(value, str)
        assert value

    def test_returns_attribute_for_existing_record_attribute(
        self, info_log_record: logging.LogRecord
    ) -> None:
        """Test that an existing record attribute is returned as-is."""
        formatter = BaseStructuredFormatter(fmt="%(levelname)s")
        assert formatter._get_field_value(info_log_record, "levelname") == "INFO"

    def test_returns_none_for_missing_record_attribute(
        self, info_log_record: logging.LogRecord
    ) -> None:
        """Test that an unknown specifier resolves to `None`."""
        formatter = BaseStructuredFormatter(fmt="%(message)s")
        assert formatter._get_field_value(info_log_record, "does_not_exist") is None


class TestHandleComplexValue:
    """Test suite for `BaseStructuredFormatter._handle_complex_value`."""

    def test_handles_dict_value(self) -> None:
        """Test that dict values are processed recursively into stringified values."""
        formatter = BaseStructuredFormatter(fmt="%(message)s")
        assert formatter._handle_complex_value({"a": 1, "b": 2}) == {
            "a": "1",
            "b": "2",
        }

    def test_handles_nested_dict_value(self) -> None:
        """Test that nested dicts are recursed into rather than stringified."""
        formatter = BaseStructuredFormatter(fmt="%(message)s")
        assert formatter._handle_complex_value({"outer": {"inner": 5}}) == {
            "outer": {"inner": "5"}
        }

    def test_handles_list_value(self) -> None:
        """Test that list values become lists of strings."""
        formatter = BaseStructuredFormatter(fmt="%(message)s")
        assert formatter._handle_complex_value([1, 2, 3]) == ["1", "2", "3"]

    def test_handles_tuple_value(self) -> None:
        """Test that tuple values are converted to lists of strings."""
        formatter = BaseStructuredFormatter(fmt="%(message)s")
        assert formatter._handle_complex_value((1, "two")) == ["1", "two"]

    def test_handles_scalar_value(self) -> None:
        """Test that scalar values are converted with `str`."""
        formatter = BaseStructuredFormatter(fmt="%(message)s")
        assert formatter._handle_complex_value(42) == "42"

    def test_handles_none_value(self) -> None:
        """Test that `None` is stringified rather than dropped."""
        formatter = BaseStructuredFormatter(fmt="%(message)s")
        assert formatter._handle_complex_value(None) == "None"


class TestAddException:
    """Test suite for `BaseStructuredFormatter._add_exception`."""

    def test_adds_exception_when_exc_info_present(
        self, error_with_exc_log_record: logging.LogRecord
    ) -> None:
        """Test that exception text is added when the record carries `exc_info`."""
        formatter = BaseStructuredFormatter(fmt="%(message)s")
        data: dict = {}
        formatter._add_exception(error_with_exc_log_record, data)
        assert "exception" in data
        assert "ValueError: Something went wrong" in data["exception"]

    def test_does_not_add_exception_without_exc_info(
        self, info_log_record: logging.LogRecord
    ) -> None:
        """Test that no exception key is added when `exc_info` is absent."""
        formatter = BaseStructuredFormatter(fmt="%(message)s")
        data: dict = {}
        formatter._add_exception(info_log_record, data)
        assert data == {}

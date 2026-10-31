import json
import logging
import sys

import pytest

from fastapi_logging_kit.formatters import JSONFormatter
from fastapi_logging_kit.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON

pytestmark = [
    pytest.mark.formatters,
    pytest.mark.json_formatter,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


class TestJSONFormatterFormat:
    """Test suite for `JSONFormatter.format`."""

    def test_formats_record_as_valid_json(
        self, json_formatter: JSONFormatter, info_log_record: logging.LogRecord
    ) -> None:
        """Test that the formatter emits parseable JSON containing the specifiers."""
        payload = json.loads(json_formatter.format(info_log_record))
        assert payload["levelname"] == "INFO"
        assert payload["message"] == "This is an info message"
        assert "asctime" in payload

    def test_message_without_key_value_pairs_is_preserved(
        self, json_formatter: JSONFormatter, debug_log_record: logging.LogRecord
    ) -> None:
        """Test that a plain message is kept intact when no pairs are present."""
        payload = json.loads(json_formatter.format(debug_log_record))
        assert payload["message"] == "This is a debug message"

    def test_includes_exception_when_present(
        self,
        json_formatter: JSONFormatter,
        error_with_exc_log_record: logging.LogRecord,
    ) -> None:
        """Test that exception information is embedded under the `exception` key."""
        payload = json.loads(json_formatter.format(error_with_exc_log_record))
        assert "ValueError: Something went wrong" in payload["exception"]

    def test_omits_exception_when_absent(
        self, json_formatter: JSONFormatter, error_log_record: logging.LogRecord
    ) -> None:
        """Test that no `exception` key is emitted for records without `exc_info`."""
        payload = json.loads(json_formatter.format(error_log_record))
        assert "exception" not in payload

    def test_cleans_newlines_and_tabs_from_message(
        self, json_formatter: JSONFormatter, info_log_record: logging.LogRecord
    ) -> None:
        """Test that newlines and tabs in the message are replaced with spaces."""
        info_log_record.msg = "line one\nline\ttwo"
        payload = json.loads(json_formatter.format(info_log_record))
        assert payload["message"] == "line one line two"

    def test_unknown_specifier_is_serialized_as_none_string(
        self, info_log_record: logging.LogRecord
    ) -> None:
        """Test that a specifier missing from the record becomes the string `None`."""
        formatter = JSONFormatter(fmt="%(missing_field)s | %(message)s")
        payload = json.loads(formatter.format(info_log_record))
        assert payload["missing_field"] == "None"


class TestJSONFormatterKeyValueExtraction:
    """Test suite for key=value extraction in `JSONFormatter`."""

    def test_extracts_scalar_pairs_and_strips_them_from_message(
        self, json_formatter: JSONFormatter, info_log_record: logging.LogRecord
    ) -> None:
        """Test that scalar key=value pairs are promoted to top-level JSON keys."""
        info_log_record.msg = "User logged in user_id=42 active=true"
        payload = json.loads(json_formatter.format(info_log_record))
        assert payload["user_id"] == 42
        assert payload["active"] is True
        assert payload["message"] == "User logged in"

    def test_extracts_dict_value(
        self, json_formatter: JSONFormatter, info_log_record: logging.LogRecord
    ) -> None:
        """Test that a dict-shaped value is parsed into a JSON object."""
        info_log_record.msg = "payload user={'id': 1, 'name': 'bob'}"
        payload = json.loads(json_formatter.format(info_log_record))
        assert payload["user"] == {"id": 1, "name": "bob"}

    def test_extracts_list_value(
        self, json_formatter: JSONFormatter, info_log_record: logging.LogRecord
    ) -> None:
        """Test that a list-shaped value is parsed into a JSON array."""
        info_log_record.msg = "batch items=[1, 2, 3]"
        payload = json.loads(json_formatter.format(info_log_record))
        assert payload["items"] == [1, 2, 3]

    def test_extracts_tuple_value(
        self, json_formatter: JSONFormatter, info_log_record: logging.LogRecord
    ) -> None:
        """Test that a tuple-shaped value is parsed and serialized as an array."""
        info_log_record.msg = "position point=(1, 2)"
        payload = json.loads(json_formatter.format(info_log_record))
        assert payload["point"] == [1, 2]


class TestJSONFormatterConvertValue:
    """Test suite for `JSONFormatter._convert_value`."""

    def test_converts_true_literal(self, json_formatter: JSONFormatter) -> None:
        """Test that the string `true` is converted to boolean `True`."""
        assert json_formatter._convert_value("true") is True

    def test_converts_false_literal(self, json_formatter: JSONFormatter) -> None:
        """Test that the string `false` is converted to boolean `False`."""
        assert json_formatter._convert_value("false") is False

    def test_converts_integer_literal(self, json_formatter: JSONFormatter) -> None:
        """Test that a numeric string is converted to an int."""
        assert json_formatter._convert_value("42") == 42

    def test_falls_back_to_string_for_malformed_literal(
        self, json_formatter: JSONFormatter
    ) -> None:
        """Test that an unparseable literal is returned unchanged as a string."""
        assert json_formatter._convert_value("12abc") == "12abc"


class TestJSONFormatterMessageHelpers:
    """Test suite for the message helper methods of `JSONFormatter`."""

    def test_extract_key_value_pairs_returns_empty_dict(
        self, json_formatter: JSONFormatter
    ) -> None:
        """Test that a message without pairs yields an empty dictionary."""
        assert json_formatter._extract_key_value_pairs("nothing here") == {}

    def test_remove_key_value_pairs_strips_pairs(
        self, json_formatter: JSONFormatter
    ) -> None:
        """Test that key=value substrings are removed from the message."""
        assert json_formatter._remove_key_value_pairs("hello a=1") == "hello"

    def test_clean_message_removes_whitespace_control_chars(
        self, json_formatter: JSONFormatter
    ) -> None:
        """Test that newlines and tabs are replaced and the result is stripped."""
        assert json_formatter._clean_message("\ta\nb\n") == "a b"

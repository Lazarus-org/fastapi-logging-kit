"""Contract tests: messages are never parsed as ad-hoc key/value syntax."""

import json
import logging

import pytest

from fastapi_logging_kit.formatters import JSONFormatter

pytestmark = [pytest.mark.formatters, pytest.mark.json_formatter]


def record(message: str = "message", **kwargs: object) -> logging.LogRecord:
    result = logging.makeLogRecord({"name": "api", "levelno": 20, "levelname": "INFO", "msg": message})
    result.__dict__.update(kwargs)
    return result


def test_json_valid_with_requested_fields() -> None:
    result = json.loads(JSONFormatter("%(levelname)s %(asctime)s %(message)s").format(record("hello")))
    assert result["levelname"] == "INFO"
    assert result["asctime"]
    assert result["message"] == "hello"


def test_message_is_preserved_without_interpreting_key_value_pairs() -> None:
    message = "user_id=42 active=true password=123\nnext line"
    result = json.loads(JSONFormatter("%(message)s").format(record(message)))
    assert result["message"] == message
    assert "user_id" not in result
    assert "active" not in result


def test_unknown_specifier_is_omitted() -> None:
    result = json.loads(JSONFormatter("%(missing_field)s %(message)s").format(record()))
    assert "missing_field" not in result


def test_captures_and_redacts_typed_extra_fields() -> None:
    result = json.loads(JSONFormatter("%(message)s").format(record("logged", user_id=42, api_key="private")))
    assert result["extra"]["user_id"] == 42
    assert result["extra"]["api_key"] == "[REDACTED]"


def test_exception_info_is_bounded_by_mode() -> None:
    try:
        raise ValueError("invalid")
    except ValueError:
        import sys
        exc = sys.exc_info()
    assert "ValueError" in json.loads(JSONFormatter("%(message)s").format(record("x", exc_info=exc)))["exception"]
    assert json.loads(JSONFormatter("%(message)s", structured_logging={"EXCEPTION_MODE": "type"}).format(record("x", exc_info=exc)))["exception"] == "ValueError"
    assert "exception" not in json.loads(JSONFormatter("%(message)s", structured_logging={"EXCEPTION_MODE": "omit"}).format(record("x", exc_info=exc)))


def test_pretty_json_is_explicit() -> None:
    assert "\n" not in JSONFormatter("%(message)s").format(record("x"))
    assert "\n" in JSONFormatter("%(message)s", structured_logging={"JSON_COMPACT": False}).format(record("x"))

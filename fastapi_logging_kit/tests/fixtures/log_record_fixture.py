import logging
from typing import Iterator

import pytest


def _make_record(level: int, levelname: str, msg: str) -> logging.LogRecord:
    """Build a LogRecord without going through a logger.

    Args:
        level (int): The numeric log level.
        levelname (str): The level name.
        msg (str): The log message.

    Returns:
        logging.LogRecord: The constructed record.

    """
    record = logging.LogRecord(
        name="test_logger",
        level=level,
        pathname="/path/to/module.py",
        lineno=42,
        msg=msg,
        args=(),
        exc_info=None,
    )
    record.levelname = levelname
    return record


@pytest.fixture
def debug_log_record() -> logging.LogRecord:
    """Return a DEBUG-level log record.

    Returns:
        logging.LogRecord: The record.

    """
    return _make_record(logging.DEBUG, "DEBUG", "This is a debug message")


@pytest.fixture
def info_log_record() -> logging.LogRecord:
    """Return an INFO-level log record.

    Returns:
        logging.LogRecord: The record.

    """
    return _make_record(logging.INFO, "INFO", "This is an info message")


@pytest.fixture
def error_log_record() -> logging.LogRecord:
    """Return an ERROR-level log record.

    Returns:
        logging.LogRecord: The record.

    """
    return _make_record(logging.ERROR, "ERROR", "This is an error message")


@pytest.fixture
def error_with_exc_log_record() -> Iterator[logging.LogRecord]:
    """Return an ERROR-level log record carrying exception info.

    Yields:
        logging.LogRecord: The record, with ``exc_info`` populated.

    """
    try:
        raise ValueError("Something went wrong")
    except ValueError:
        import sys

        record = _make_record(logging.ERROR, "ERROR", "This is an error message")
        record.exc_info = sys.exc_info()
        yield record

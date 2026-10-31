import os
from typing import Iterator, List

import pytest

from fastapi_logging_kit.settings.conf import LogConfig, LogManager


@pytest.fixture
def log_config() -> LogConfig:
    """Return a LogConfig covering every constructor argument.

    Returns:
        LogConfig: The configuration instance.

    """
    return LogConfig(
        log_levels=["DEBUG", "INFO"],
        log_dir="/tmp/logs",
        log_file_formats={"DEBUG": 1, "INFO": 2},
        log_file_format_types={"DEBUG": "normal", "INFO": "normal"},
        extra_log_files={"DEBUG": False, "INFO": False},
        console_level="DEBUG",
        console_format=1,
        colorize_console=False,
        log_date_format="%Y-%m-%d %H:%M:%S",
        log_email_notifier_enable=False,
        log_email_notifier_log_levels=["ERROR", None],
        log_email_notifier_log_format=1,
    )


@pytest.fixture
def log_manager(log_config: LogConfig) -> LogManager:
    """Return a LogManager built on ``log_config``.

    Args:
        log_config (LogConfig): The configuration to manage.

    Returns:
        LogManager: The manager instance.

    """
    return LogManager(log_config)


@pytest.fixture
def temp_log_directory(tmp_path: object) -> Iterator[str]:
    """Create an empty log directory.

    Args:
        tmp_path (object): pytest's temporary directory.

    Yields:
        str: The path to the log directory.

    """
    log_dir = os.path.join(str(tmp_path), "logs")
    os.makedirs(log_dir, exist_ok=True)
    yield log_dir


@pytest.fixture
def temp_json_log_directory(temp_log_directory: str) -> Iterator[str]:
    """Create a log directory containing a ``json`` subdirectory with a file.

    Args:
        temp_log_directory (str): The base log directory.

    Yields:
        str: The path to the log directory.

    """
    json_dir = os.path.join(temp_log_directory, "json")
    os.makedirs(json_dir, exist_ok=True)
    with open(os.path.join(json_dir, "test.json"), "w", encoding="utf-8") as f:
        f.write('{"message": "first"}\n{"message": "second"}\n')
    yield temp_log_directory


@pytest.fixture
def temp_xml_log_directory(temp_log_directory: str) -> Iterator[str]:
    """Create a log directory containing an ``xml`` subdirectory with a file.

    Args:
        temp_log_directory (str): The base log directory.

    Yields:
        str: The path to the log directory.

    """
    xml_dir = os.path.join(temp_log_directory, "xml")
    os.makedirs(xml_dir, exist_ok=True)
    with open(os.path.join(xml_dir, "test.xml"), "w", encoding="utf-8") as f:
        f.write("<log><message>hello</message></log>\n")
    yield temp_log_directory


@pytest.fixture
def log_dir_with_rotated_files(temp_log_directory: str) -> Iterator[str]:
    """Create a log directory holding active, rotated and compressed files.

    Args:
        temp_log_directory (str): The base log directory.

    Yields:
        str: The path to the log directory.

    """
    files: List[str] = [
        "info.log",  # active
        "info.log.1",  # rotated
        "error.log",  # active
        "error.log.2024-01-15",  # rotated
        "debug.log.1.gz",  # compressed
    ]
    for name in files:
        with open(os.path.join(temp_log_directory, name), "wb") as f:
            f.write(b"log line\n")

    yield temp_log_directory

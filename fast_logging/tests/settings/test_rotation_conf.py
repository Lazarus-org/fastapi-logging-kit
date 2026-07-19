import sys
from typing import Any, Dict

import pytest

from fast_logging.settings.conf import LogConfig, LogManager
from fast_logging.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON

pytestmark = [
    pytest.mark.settings,
    pytest.mark.settings_rotation_conf,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


def build_manager(**rotation_kwargs: Any) -> LogManager:
    """Build a LogManager whose config carries the given rotation settings."""
    kwargs: Dict[str, Any] = {
        "log_levels": ["DEBUG", "INFO"],
        "log_dir": "/tmp/logs",
        "log_file_formats": {"DEBUG": 1, "INFO": 1},
        "log_file_format_types": {"DEBUG": "normal", "INFO": "normal"},
        "extra_log_files": {"DEBUG": False, "INFO": False},
        "console_level": "DEBUG",
        "console_format": 1,
        "colorize_console": False,
        "log_date_format": "%Y-%m-%d %H:%M:%S",
        "log_email_notifier_enable": False,
        "log_email_notifier_log_levels": ["ERROR", None],
        "log_email_notifier_log_format": 1,
    }
    kwargs.update(rotation_kwargs)
    return LogManager(LogConfig(**kwargs))


class TestNoRotationHandler:
    """Test suite for the ``TYPE = "none"`` rotation strategy."""

    def test_plain_file_handler_is_used(self) -> None:
        """Test that no rotation yields a plain `logging.FileHandler`."""
        manager = build_manager(log_rotation={"TYPE": "none"})
        handler = manager._build_file_handler_config("/tmp/logs/debug.log", "DEBUG")

        assert handler == {
            "class": "logging.FileHandler",
            "filename": "/tmp/logs/debug.log",
        }

    def test_default_rotation_is_none(self) -> None:
        """Test that the default rotation config produces a plain FileHandler."""
        manager = build_manager()
        handler = manager._build_file_handler_config("/tmp/logs/info.log", "INFO")

        assert handler["class"] == "logging.FileHandler"


class TestSizeRotationHandler:
    """Test suite for the ``TYPE = "size"`` rotation strategy."""

    def test_uncompressed_size_rotation(self) -> None:
        """Test that size rotation without compression uses RotatingFileHandler."""
        manager = build_manager(
            log_rotation={
                "TYPE": "size",
                "MAX_BYTES": 2048,
                "BACKUP_COUNT": 3,
                "COMPRESS": False,
            }
        )
        handler = manager._build_file_handler_config("/tmp/logs/debug.log", "DEBUG")

        assert handler["class"] == "logging.handlers.RotatingFileHandler"
        assert handler["maxBytes"] == 2048
        assert handler["backupCount"] == 3
        assert handler["filename"] == "/tmp/logs/debug.log"

    def test_compressed_size_rotation(self) -> None:
        """Test that COMPRESS selects the compressed rotating handler."""
        manager = build_manager(
            log_rotation={"TYPE": "size", "COMPRESS": True, "MAX_BYTES": 4096}
        )
        handler = manager._build_file_handler_config("/tmp/logs/debug.log", "DEBUG")

        assert handler["class"] == "fast_logging.handlers.CompressedRotatingFileHandler"
        assert handler["maxBytes"] == 4096

    def test_size_rotation_uses_defaults_for_missing_keys(self) -> None:
        """Test that missing size-rotation keys fall back to their defaults."""
        manager = build_manager(log_rotation={"TYPE": "SIZE"})
        handler = manager._build_file_handler_config("/tmp/logs/debug.log", "DEBUG")

        assert handler["class"] == "logging.handlers.RotatingFileHandler"
        assert handler["maxBytes"] == 10_485_760
        assert handler["backupCount"] == 5


class TestTimeRotationHandler:
    """Test suite for the ``TYPE = "time"`` rotation strategy."""

    def test_uncompressed_time_rotation(self) -> None:
        """Test that time rotation uses TimedRotatingFileHandler."""
        manager = build_manager(
            log_rotation={
                "TYPE": "time",
                "WHEN": "h",
                "INTERVAL": 6,
                "BACKUP_COUNT": 2,
                "COMPRESS": False,
            }
        )
        handler = manager._build_file_handler_config("/tmp/logs/info.log", "INFO")

        assert handler["class"] == "logging.handlers.TimedRotatingFileHandler"
        assert handler["when"] == "h"
        assert handler["interval"] == 6
        assert handler["backupCount"] == 2

    def test_compressed_time_rotation(self) -> None:
        """Test that COMPRESS selects the compressed timed rotating handler."""
        manager = build_manager(log_rotation={"TYPE": "time", "COMPRESS": True})
        handler = manager._build_file_handler_config("/tmp/logs/info.log", "INFO")

        assert (
            handler["class"]
            == "fast_logging.handlers.CompressedTimedRotatingFileHandler"
        )

    def test_time_rotation_uses_defaults_for_missing_keys(self) -> None:
        """Test that missing time-rotation keys fall back to their defaults."""
        manager = build_manager(log_rotation={"TYPE": "time"})
        handler = manager._build_file_handler_config("/tmp/logs/info.log", "INFO")

        assert handler["when"] == "midnight"
        assert handler["interval"] == 1


class TestPerLevelRotationOverrides:
    """Test suite for per-level rotation overrides in handler building."""

    def test_override_changes_handler_class_for_one_level(self) -> None:
        """Test that only the overridden level gets the alternate handler."""
        manager = build_manager(
            log_rotation={"TYPE": "none"},
            log_rotation_overrides={"INFO": {"TYPE": "size", "MAX_BYTES": 512}},
        )

        debug_handler = manager._build_file_handler_config("/tmp/d.log", "DEBUG")
        info_handler = manager._build_file_handler_config("/tmp/i.log", "INFO")

        assert debug_handler["class"] == "logging.FileHandler"
        assert info_handler["class"] == "logging.handlers.RotatingFileHandler"
        assert info_handler["maxBytes"] == 512

    def test_rotation_reflected_in_set_conf(self, temp_log_directory: str) -> None:
        """Test that the rotation handler classes reach the dictConfig payload."""
        from unittest.mock import patch

        manager = build_manager(
            log_dir=temp_log_directory,
            log_rotation={"TYPE": "size", "MAX_BYTES": 1024},
            log_rotation_overrides={"INFO": {"TYPE": "time", "WHEN": "d"}},
        )
        manager.create_log_files()

        with patch("logging.config.dictConfig") as mock_dict_config:
            manager.set_conf()

        handlers = mock_dict_config.call_args[0][0]["handlers"]
        assert handlers["debug"]["class"] == "logging.handlers.RotatingFileHandler"
        assert handlers["info"]["class"] == "logging.handlers.TimedRotatingFileHandler"
        assert handlers["info"]["when"] == "d"

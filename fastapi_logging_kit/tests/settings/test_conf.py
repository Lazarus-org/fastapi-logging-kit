import os
import sys
from typing import Any, Dict, List
from unittest.mock import patch

import pytest

from fastapi_logging_kit.constants import FORMAT_OPTIONS
from fastapi_logging_kit.settings.conf import LogConfig, LogManager
from fastapi_logging_kit.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON

pytestmark = [
    pytest.mark.settings,
    pytest.mark.settings_conf,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


def build_config(**overrides: Any) -> LogConfig:
    """Build a LogConfig with sensible defaults, overridden by ``overrides``."""
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
    kwargs.update(overrides)
    return LogConfig(**kwargs)


class TestLogConfigFileFormats:
    """Test suite for `LogConfig._resolve_file_formats`."""

    def test_integer_format_is_looked_up(self) -> None:
        """Test that an integer format resolves through FORMAT_OPTIONS."""
        config = build_config(log_file_formats={"DEBUG": 2, "INFO": 3})

        assert config.log_file_formats["DEBUG"] == FORMAT_OPTIONS[2]
        assert config.log_file_formats["INFO"] == FORMAT_OPTIONS[3]

    def test_unknown_integer_format_falls_back_to_option_one(self) -> None:
        """Test that an out-of-range integer format falls back to option 1."""
        config = build_config(log_file_formats={"DEBUG": 999, "INFO": 1})
        assert config.log_file_formats["DEBUG"] == FORMAT_OPTIONS[1]

    def test_string_format_is_used_verbatim(self) -> None:
        """Test that a string format is kept as provided."""
        config = build_config(
            log_file_formats={"DEBUG": "%(levelname)s - %(message)s", "INFO": 1}
        )
        assert config.log_file_formats["DEBUG"] == "%(levelname)s - %(message)s"

    def test_missing_level_falls_back_to_option_one(self) -> None:
        """Test that a level absent from the mapping uses format option 1."""
        config = build_config(log_file_formats={"DEBUG": 1})
        assert config.log_file_formats["INFO"] == FORMAT_OPTIONS[1]

    def test_falsy_format_falls_back_to_option_one(self) -> None:
        """Test that a falsy format value uses format option 1."""
        config = build_config(log_file_formats={"DEBUG": 0, "INFO": ""})

        assert config.log_file_formats["DEBUG"] == FORMAT_OPTIONS[1]
        assert config.log_file_formats["INFO"] == FORMAT_OPTIONS[1]

    def test_ansi_sequences_are_stripped_from_file_formats(self) -> None:
        """Test that color codes never reach the file formats."""
        config = build_config(
            log_file_formats={"DEBUG": "\x1b[31m%(message)s\x1b[0m", "INFO": 1}
        )
        assert config.log_file_formats["DEBUG"] == "%(message)s"


class TestRemoveAnsiEscapeSequences:
    """Test suite for `LogConfig.remove_ansi_escape_sequences`."""

    def test_strips_escape_sequences(self) -> None:
        """Test that ANSI escape sequences are removed."""
        assert (
            LogConfig.remove_ansi_escape_sequences("\x1b[31mred\x1b[0m text") == "red text"
        )

    def test_leaves_plain_text_untouched(self) -> None:
        """Test that a string without escape sequences is returned unchanged."""
        assert LogConfig.remove_ansi_escape_sequences("plain text") == "plain text"


class TestResolveFormat:
    """Test suite for `LogConfig.resolve_format`."""

    def test_integer_format(self) -> None:
        """Test that an integer resolves through FORMAT_OPTIONS."""
        assert LogConfig.resolve_format(4) == FORMAT_OPTIONS[4]

    def test_unknown_integer_format(self) -> None:
        """Test that an unknown integer falls back to format option 1."""
        assert LogConfig.resolve_format(999) == FORMAT_OPTIONS[1]

    def test_string_format(self) -> None:
        """Test that a string format is returned as provided."""
        assert LogConfig.resolve_format("%(message)s") == "%(message)s"

    def test_falsy_format_uses_option_one(self) -> None:
        """Test that a falsy format resolves to format option 1."""
        assert LogConfig.resolve_format(0) == FORMAT_OPTIONS[1]
        assert LogConfig.resolve_format("") == FORMAT_OPTIONS[1]

    def test_unsupported_type_resolves_to_empty_string(self) -> None:
        """Test that a truthy value of an unsupported type yields an empty string."""
        assert LogConfig.resolve_format([1, 2]) == ""  # type: ignore[arg-type]

    def test_colors_kept_when_use_colors_is_true(self) -> None:
        """Test that escape sequences survive when colors are enabled."""
        assert (
            LogConfig.resolve_format("\x1b[31m%(message)s", use_colors=True)
            == "\x1b[31m%(message)s"
        )

    def test_colors_stripped_when_use_colors_is_false(self) -> None:
        """Test that escape sequences are stripped when colors are disabled."""
        assert (
            LogConfig.resolve_format("\x1b[31m%(message)s", use_colors=False)
            == "%(message)s"
        )


class TestLogConfigInitialization:
    """Test suite for the `LogConfig` constructor."""

    def test_attributes_are_stored(self, log_config: LogConfig) -> None:
        """Test that the constructor stores the supplied configuration."""
        assert log_config.log_levels == ["DEBUG", "INFO"]
        assert log_config.log_dir == "/tmp/logs"
        assert log_config.console_level == "DEBUG"
        assert log_config.colorize_console is False
        assert log_config.email_notifier_enable is False
        assert log_config.email_notifier_log_levels == ["ERROR", None]

    def test_console_format_respects_colorize(self) -> None:
        """Test that the console format keeps colors when colorize is on."""
        colored = build_config(
            colorize_console=True, console_format="\x1b[31m%(message)s"
        )
        plain = build_config(
            colorize_console=False, console_format="\x1b[31m%(message)s"
        )

        assert colored.console_format == "\x1b[31m%(message)s"
        assert plain.console_format == "%(message)s"


class TestRotationConfig:
    """Test suite for rotation configuration on `LogConfig`."""

    def test_rotation_defaults_when_not_supplied(self) -> None:
        """Test that omitting rotation falls back to the packaged defaults."""
        config = build_config()

        assert config.log_rotation["TYPE"] == "none"
        assert config.log_rotation["BACKUP_COUNT"] == 5
        assert config.log_rotation_overrides == {}

    def test_supplied_rotation_merges_over_defaults(self) -> None:
        """Test that a partial rotation config merges on top of the defaults."""
        config = build_config(log_rotation={"TYPE": "size", "MAX_BYTES": 1024})

        assert config.log_rotation["TYPE"] == "size"
        assert config.log_rotation["MAX_BYTES"] == 1024
        assert config.log_rotation["BACKUP_COUNT"] == 5

    def test_get_rotation_config_without_override(self) -> None:
        """Test that a level without an override gets the global config."""
        config = build_config(log_rotation={"TYPE": "size"})
        assert config.get_rotation_config_for_level("DEBUG")["TYPE"] == "size"

    def test_get_rotation_config_with_override(self) -> None:
        """Test that a per-level override is merged over the global config."""
        config = build_config(
            log_rotation={"TYPE": "size", "BACKUP_COUNT": 5},
            log_rotation_overrides={"ERROR": {"TYPE": "time", "BACKUP_COUNT": 10}},
        )
        effective = config.get_rotation_config_for_level("ERROR")

        assert effective["TYPE"] == "time"
        assert effective["BACKUP_COUNT"] == 10
        # the global config is not mutated
        assert config.log_rotation["TYPE"] == "size"


class TestLogManagerFileCreation:
    """Test suite for `LogManager.create_log_files` and `get_log_file`."""

    def test_creates_regular_log_files(self, temp_log_directory: str) -> None:
        """Test that a normal format type produces `<level>.log` files."""
        manager = LogManager(build_config(log_dir=temp_log_directory))
        manager.create_log_files()

        for level in ("DEBUG", "INFO"):
            expected = os.path.join(temp_log_directory, f"{level.lower()}.log")
            assert manager.log_files[level] == expected
            assert os.path.exists(expected)

    def test_creates_typed_json_and_xml_files(self, temp_log_directory: str) -> None:
        """Test that EXTRA_LOG_FILES routes JSON/XML levels into subdirectories."""
        manager = LogManager(
            build_config(
                log_dir=temp_log_directory,
                log_file_format_types={"DEBUG": "JSON", "INFO": "XML"},
                extra_log_files={"DEBUG": True, "INFO": True},
            )
        )
        manager.create_log_files()

        json_file = os.path.join(temp_log_directory, "json", "debug.json")
        xml_file = os.path.join(temp_log_directory, "xml", "info.xml")

        assert manager.log_files["DEBUG"] == json_file
        assert manager.log_files["INFO"] == xml_file
        assert os.path.exists(json_file)
        assert os.path.exists(xml_file)

    def test_extra_file_with_unsupported_type_uses_regular_file(
        self, temp_log_directory: str
    ) -> None:
        """Test that an extra file of a non-JSON/XML type stays a plain log."""
        manager = LogManager(
            build_config(
                log_dir=temp_log_directory,
                log_file_format_types={"DEBUG": "FLAT", "INFO": "normal"},
                extra_log_files={"DEBUG": True, "INFO": True},
            )
        )
        manager.create_log_files()

        assert manager.log_files["DEBUG"] == os.path.join(
            temp_log_directory, "debug.log"
        )

    def test_missing_format_type_defaults_to_regular_file(
        self, temp_log_directory: str
    ) -> None:
        """Test that a level with no declared format type gets a plain log file."""
        manager = LogManager(
            build_config(log_dir=temp_log_directory, log_file_format_types={})
        )
        manager.create_log_files()

        assert manager.log_files["INFO"] == os.path.join(temp_log_directory, "info.log")

    def test_existing_file_is_not_truncated(self, temp_log_directory: str) -> None:
        """Test that an already-present log file is left untouched."""
        existing = os.path.join(temp_log_directory, "debug.log")
        with open(existing, "w", encoding="utf-8") as handle:
            handle.write("keep me")

        manager = LogManager(build_config(log_dir=temp_log_directory))
        manager.create_log_files()

        with open(existing, encoding="utf-8") as handle:
            assert handle.read() == "keep me"

    def test_get_log_file_hit(self, temp_log_directory: str) -> None:
        """Test that `get_log_file` returns the path for a known level."""
        manager = LogManager(build_config(log_dir=temp_log_directory))
        manager.create_log_files()

        assert manager.get_log_file("DEBUG") == os.path.join(
            temp_log_directory, "debug.log"
        )

    def test_get_log_file_miss(self, log_manager: LogManager) -> None:
        """Test that `get_log_file` returns None for an unknown level."""
        assert log_manager.get_log_file("CRITICAL") is None


class TestSetConf:
    """Test suite for `LogManager.set_conf`."""

    def test_builds_expected_dict_config(self, temp_log_directory: str) -> None:
        """Test that the generated dictConfig contains the expected sections."""
        manager = LogManager(build_config(log_dir=temp_log_directory))
        manager.create_log_files()

        with patch("logging.config.dictConfig") as mock_dict_config:
            manager.set_conf()

        config = mock_dict_config.call_args[0][0]
        assert config["version"] == 1
        assert config["disable_existing_loggers"] is False
        assert set(config["loggers"]) == {"debug", "info"}
        assert "console" in config["handlers"]
        assert "context_var_filter" in config["filters"]
        assert config["root"]["handlers"] == list(config["handlers"].keys())

    def test_email_handlers_added_when_notifier_enabled(
        self, temp_log_directory: str
    ) -> None:
        """Test that enabling the notifier registers per-level email handlers."""
        manager = LogManager(
            build_config(
                log_dir=temp_log_directory,
                log_email_notifier_enable=True,
                log_email_notifier_log_levels=["ERROR", "CRITICAL"],
            )
        )
        manager.create_log_files()

        with patch("logging.config.dictConfig") as mock_dict_config:
            manager.set_conf()

        handlers = mock_dict_config.call_args[0][0]["handlers"]
        assert "email_error" in handlers
        assert "email_critical" in handlers
        assert handlers["email_error"]["class"] == "fastapi_logging_kit.handlers.EmailHandler"

    def test_email_handlers_omitted_when_notifier_disabled(
        self, temp_log_directory: str
    ) -> None:
        """Test that no email handlers are added when the notifier is off."""
        manager = LogManager(
            build_config(
                log_dir=temp_log_directory,
                log_email_notifier_enable=False,
                log_email_notifier_log_levels=["ERROR", "CRITICAL"],
            )
        )
        manager.create_log_files()

        with patch("logging.config.dictConfig") as mock_dict_config:
            manager.set_conf()

        handlers = mock_dict_config.call_args[0][0]["handlers"]
        assert not [name for name in handlers if name.startswith("email_")]

    def test_colored_formatter_used_when_colorize_enabled(
        self, temp_log_directory: str
    ) -> None:
        """Test that the console formatter is colorized when requested."""
        manager = LogManager(
            build_config(log_dir=temp_log_directory, colorize_console=True)
        )
        manager.create_log_files()

        with patch("logging.config.dictConfig") as mock_dict_config:
            manager.set_conf()

        console = mock_dict_config.call_args[0][0]["formatters"]["console"]
        assert console["()"] == "fastapi_logging_kit.formatters.ColoredFormatter"

    def test_plain_formatter_used_when_colorize_disabled(
        self, temp_log_directory: str
    ) -> None:
        """Test that the console formatter has no factory when colors are off."""
        manager = LogManager(
            build_config(log_dir=temp_log_directory, colorize_console=False)
        )
        manager.create_log_files()

        with patch("logging.config.dictConfig") as mock_dict_config:
            manager.set_conf()

        console = mock_dict_config.call_args[0][0]["formatters"]["console"]
        assert "()" not in console

    def test_structured_formatters_get_a_factory(
        self, temp_log_directory: str
    ) -> None:
        """Test that JSON/XML/FLAT levels are given the matching formatter class."""
        manager = LogManager(
            build_config(
                log_dir=temp_log_directory,
                log_levels=["DEBUG", "INFO"],
                log_file_format_types={"DEBUG": "JSON", "INFO": "normal"},
            )
        )
        manager.create_log_files()

        with patch("logging.config.dictConfig") as mock_dict_config:
            manager.set_conf()

        formatters = mock_dict_config.call_args[0][0]["formatters"]
        assert formatters["debug"]["()"] == "fastapi_logging_kit.formatters.JSONFormatter"
        assert "()" not in formatters["info"]

    def test_missing_format_type_gets_no_factory(
        self, temp_log_directory: str
    ) -> None:
        """Test that a level with no declared format type gets a plain formatter."""
        manager = LogManager(
            build_config(log_dir=temp_log_directory, log_file_format_types={})
        )
        manager.create_log_files()

        with patch("logging.config.dictConfig") as mock_dict_config:
            manager.set_conf()

        formatters = mock_dict_config.call_args[0][0]["formatters"]
        assert "()" not in formatters["debug"]

    def test_applies_configuration_for_real(self, temp_log_directory: str) -> None:
        """Test that `set_conf` installs a working logging configuration."""
        import logging

        manager = LogManager(build_config(log_dir=temp_log_directory))
        manager.create_log_files()
        manager.set_conf()

        debug_logger = logging.getLogger("debug")
        assert debug_logger.level == logging.DEBUG
        assert debug_logger.propagate is False
        assert debug_logger.handlers

        logging.config.dictConfig(
            {"version": 1, "disable_existing_loggers": False, "root": {"handlers": []}}
        )

    def test_file_handler_filters_reference_the_level(
        self, temp_log_directory: str
    ) -> None:
        """Test that each file handler filters on its own level plus context."""
        manager = LogManager(build_config(log_dir=temp_log_directory))
        manager.create_log_files()

        with patch("logging.config.dictConfig") as mock_dict_config:
            manager.set_conf()

        handlers = mock_dict_config.call_args[0][0]["handlers"]
        assert handlers["debug"]["filters"] == ["debug", "context_var_filter"]
        assert handlers["debug"]["formatter"] == "debug"
        assert handlers["debug"]["level"] == "DEBUG"


class TestNotifierLevelsList:
    """Test suite covering how notifier levels shape the email handlers."""

    def test_none_entries_are_skipped(self, temp_log_directory: str) -> None:
        """Test that ``None`` entries in the notifier levels create no handler."""
        levels: List[Any] = ["ERROR", None]
        manager = LogManager(
            build_config(
                log_dir=temp_log_directory,
                log_email_notifier_enable=True,
                log_email_notifier_log_levels=levels,
            )
        )
        manager.create_log_files()

        with patch("logging.config.dictConfig") as mock_dict_config:
            manager.set_conf()

        handlers = mock_dict_config.call_args[0][0]["handlers"]
        assert "email_error" in handlers
        assert len([name for name in handlers if name.startswith("email_")]) == 1

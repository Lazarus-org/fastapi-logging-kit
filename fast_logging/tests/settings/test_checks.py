import sys
from types import MappingProxyType
from typing import Any, Dict, List

import pytest

from fast_logging.checks import Error
from fast_logging.settings import settings_manager
from fast_logging.settings.checks import check_logging_settings
from fast_logging.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON

pytestmark = [
    pytest.mark.settings,
    pytest.mark.settings_checks,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


def error_ids(errors: List[Error]) -> List[str]:
    """Return the ids of the supplied errors."""
    return [error.id for error in errors if error.id]


def valid_config(log_dir: str) -> Dict[str, Any]:
    """Return a fully valid configuration rooted at ``log_dir``."""
    return {
        "LOG_DIR": log_dir,
        "LOG_FILE_LEVELS": ["DEBUG", "INFO"],
        "LOG_FILE_FORMATS": {"DEBUG": 1, "INFO": "%(message)s"},
        "LOG_FILE_FORMAT_TYPES": {"DEBUG": "normal", "INFO": "JSON"},
        "EXTRA_LOG_FILES": {"DEBUG": False, "INFO": True},
        "LOG_CONSOLE_LEVEL": "DEBUG",
        "LOG_CONSOLE_FORMAT": 1,
        "LOG_CONSOLE_COLORIZE": True,
        "LOG_DATE_FORMAT": "%Y-%m-%d %H:%M:%S",
        "INCLUDE_LOG_iBOARD": False,
        "AUTO_INITIALIZATION_ENABLE": True,
        "INITIALIZATION_MESSAGE_ENABLE": True,
        "LOG_SQL_QUERIES_ENABLE": False,
        "LOG_DIR_SIZE_LIMIT": 100,
        "LOG_EMAIL_NOTIFIER": {
            "ENABLE": False,
            "NOTIFY_ERROR": True,
            "NOTIFY_CRITICAL": False,
            "LOG_FORMAT": 1,
            "USE_TEMPLATE": True,
        },
    }


class TestValidLoggingSettings:
    """Test suite for `check_logging_settings` with a valid configuration."""

    def test_valid_configuration_reports_no_errors(
        self, temp_log_directory: str
    ) -> None:
        """Test that a fully valid configuration produces no errors."""
        settings_manager.load(valid_config(temp_log_directory))
        assert check_logging_settings({}) == []

    def test_valid_configuration_with_email_notifier_enabled(
        self, temp_log_directory: str, admin_email_mock_settings: Dict[str, Any]
    ) -> None:
        """Test that an enabled notifier with full SMTP settings is accepted."""
        config = valid_config(temp_log_directory)
        config["LOG_EMAIL_NOTIFIER"]["ENABLE"] = True
        config["EMAIL"] = admin_email_mock_settings
        settings_manager.load(config)

        assert check_logging_settings({}) == []


class TestInvalidLoggingSettings:
    """Test suite for the individual failure branches of `check_logging_settings`."""

    def test_invalid_log_dir_type(self, temp_log_directory: str) -> None:
        """Test that a non-string LOG_DIR reports E001."""
        config = valid_config(temp_log_directory)
        config["LOG_DIR"] = 12345
        settings_manager.load(config)

        assert "fast_logging.E001_LOG_DIR" in error_ids(check_logging_settings({}))

    def test_invalid_log_file_levels(self, temp_log_directory: str) -> None:
        """Test that an unknown level in LOG_FILE_LEVELS reports E007."""
        config = valid_config(temp_log_directory)
        config["LOG_FILE_LEVELS"] = ["INVALID"]
        settings_manager.load(config)

        assert "fast_logging.E007_LOG_FILE_LEVELS" in error_ids(
            check_logging_settings({})
        )

    def test_log_file_formats_not_a_dict(self, temp_log_directory: str) -> None:
        """Test that a non-dict LOG_FILE_FORMATS reports E020."""
        config = valid_config(temp_log_directory)
        config["LOG_FILE_FORMATS"] = ["not", "a", "dict"]
        settings_manager.load(config)

        assert "fast_logging.E020_LOG_FILE_FORMATS" in error_ids(
            check_logging_settings({})
        )

    def test_invalid_level_key_in_log_file_formats(
        self, temp_log_directory: str
    ) -> None:
        """Test that an unknown level key in LOG_FILE_FORMATS reports E019."""
        config = valid_config(temp_log_directory)
        config["LOG_FILE_FORMATS"] = {"NOT_A_LEVEL": 1}
        settings_manager.load(config)

        assert "fast_logging.E019_LOG_FILE_FORMATS" in error_ids(
            check_logging_settings({})
        )

    def test_invalid_format_option_in_log_file_formats(
        self, temp_log_directory: str
    ) -> None:
        """Test that a bad format option inside LOG_FILE_FORMATS is reported."""
        config = valid_config(temp_log_directory)
        config["LOG_FILE_FORMATS"] = {"DEBUG": 999}
        settings_manager.load(config)

        assert "fast_logging.E012_LOG_FILE_FORMATS['DEBUG']" in error_ids(
            check_logging_settings({})
        )

    def test_invalid_log_file_format_types(self, temp_log_directory: str) -> None:
        """Test that an unsupported file format type reports E024."""
        config = valid_config(temp_log_directory)
        config["LOG_FILE_FORMAT_TYPES"] = {"DEBUG": "YAML"}
        settings_manager.load(config)

        assert "fast_logging.E024_LOG_FILE_FORMAT_TYPES" in error_ids(
            check_logging_settings({})
        )

    def test_invalid_extra_log_files(self, temp_log_directory: str) -> None:
        """Test that a non-boolean EXTRA_LOG_FILES value reports E027."""
        config = valid_config(temp_log_directory)
        config["EXTRA_LOG_FILES"] = {"DEBUG": "yes"}
        settings_manager.load(config)

        assert "fast_logging.E027_EXTRA_LOG_FILES" in error_ids(
            check_logging_settings({})
        )

    def test_invalid_console_format(self, temp_log_directory: str) -> None:
        """Test that an invalid console format option reports E012."""
        config = valid_config(temp_log_directory)
        config["LOG_CONSOLE_FORMAT"] = 999
        settings_manager.load(config)

        assert "fast_logging.E012_LOG_CONSOLE_FORMAT" in error_ids(
            check_logging_settings({})
        )

    def test_invalid_console_level(self, temp_log_directory: str) -> None:
        """Test that an unknown console level reports E007."""
        config = valid_config(temp_log_directory)
        config["LOG_CONSOLE_LEVEL"] = "TRACE"
        settings_manager.load(config)

        assert "fast_logging.E007_LOG_CONSOLE_LEVEL" in error_ids(
            check_logging_settings({})
        )

    def test_invalid_console_colorize(self, temp_log_directory: str) -> None:
        """Test that a non-boolean LOG_CONSOLE_COLORIZE reports E014."""
        config = valid_config(temp_log_directory)
        config["LOG_CONSOLE_COLORIZE"] = "true"
        settings_manager.load(config)

        assert "fast_logging.E014_LOG_CONSOLE_COLORIZE" in error_ids(
            check_logging_settings({})
        )

    def test_invalid_date_format(self, temp_log_directory: str) -> None:
        """Test that an invalid strftime directive reports E016."""
        config = valid_config(temp_log_directory)
        config["LOG_DATE_FORMAT"] = "%Q-%Z"
        settings_manager.load(config)

        assert "fast_logging.E016_LOG_DATE_FORMAT" in error_ids(
            check_logging_settings({})
        )

    def test_invalid_include_log_iboard(self, temp_log_directory: str) -> None:
        """Test that a non-boolean INCLUDE_LOG_iBOARD reports E014."""
        config = valid_config(temp_log_directory)
        config["INCLUDE_LOG_iBOARD"] = "no"
        settings_manager.load(config)

        assert "fast_logging.E014_INCLUDE_LOG_iBOARD" in error_ids(
            check_logging_settings({})
        )

    def test_invalid_auto_initialization_enable(self, temp_log_directory: str) -> None:
        """Test that a non-boolean AUTO_INITIALIZATION_ENABLE reports E014."""
        config = valid_config(temp_log_directory)
        config["AUTO_INITIALIZATION_ENABLE"] = "yes"
        settings_manager.load(config)

        assert "fast_logging.E014_AUTO_INITIALIZATION_ENABLE" in error_ids(
            check_logging_settings({})
        )

    def test_invalid_initialization_message_enable(
        self, temp_log_directory: str
    ) -> None:
        """Test that a non-boolean INITIALIZATION_MESSAGE_ENABLE reports E014."""
        config = valid_config(temp_log_directory)
        config["INITIALIZATION_MESSAGE_ENABLE"] = 1
        settings_manager.load(config)

        assert "fast_logging.E014_INITIALIZATION_MESSAGE_ENABLE" in error_ids(
            check_logging_settings({})
        )

    def test_invalid_log_sql_queries_enable(self, temp_log_directory: str) -> None:
        """Test that a non-boolean LOG_SQL_QUERIES_ENABLE reports E014."""
        config = valid_config(temp_log_directory)
        config["LOG_SQL_QUERIES_ENABLE"] = "off"
        settings_manager.load(config)

        assert "fast_logging.E014_LOG_SQL_QUERIES_ENABLE" in error_ids(
            check_logging_settings({})
        )

    def test_invalid_log_dir_size_limit(self, temp_log_directory: str) -> None:
        """Test that a negative LOG_DIR_SIZE_LIMIT reports E019."""
        config = valid_config(temp_log_directory)
        config["LOG_DIR_SIZE_LIMIT"] = -1
        settings_manager.load(config)

        assert "fast_logging.E019_LOG_DIR_SIZE_LIMIT" in error_ids(
            check_logging_settings({})
        )

    def test_non_dict_email_notifier_reports_e017(
        self, temp_log_directory: str
    ) -> None:
        """Test that a mapping-but-not-dict LOG_EMAIL_NOTIFIER reports E017."""
        config = valid_config(temp_log_directory)
        config["LOG_EMAIL_NOTIFIER"] = MappingProxyType({"ENABLE": False})
        settings_manager.load(config)

        assert "fast_logging.E017_LOG_EMAIL_NOTIFIER" in error_ids(
            check_logging_settings({})
        )

    def test_string_email_notifier_reports_e017(
        self, temp_log_directory: str
    ) -> None:
        """Test that a LOG_EMAIL_NOTIFIER with no mapping interface reports E017.

        Loading must not raise on a malformed value: the misconfiguration
        has to survive as far as the validators so the user gets the
        actionable error rather than an AttributeError traceback.

        """
        config = valid_config(temp_log_directory)
        config["LOG_EMAIL_NOTIFIER"] = "enabled"
        settings_manager.load(config)

        assert settings_manager.email_notifier_enabled is False
        assert "fast_logging.E017_LOG_EMAIL_NOTIFIER" in error_ids(
            check_logging_settings({})
        )

    def test_notifier_key_with_unexpected_type(
        self, temp_log_directory: str
    ) -> None:
        """Test that a notifier value of an unexpected type reports E018."""
        config = valid_config(temp_log_directory)
        config["LOG_EMAIL_NOTIFIER"]["NOTIFY_ERROR"] = ["yes"]
        settings_manager.load(config)

        assert "fast_logging.E018_LOG_EMAIL_NOTIFIER['NOTIFY_ERROR']" in error_ids(
            check_logging_settings({})
        )


class TestEmailSettingsCheck:
    """Test suite for the email-settings branch of `check_logging_settings`."""

    def test_missing_email_settings_when_notifier_enabled(
        self, temp_log_directory: str
    ) -> None:
        """Test that enabling the notifier without SMTP settings reports E021."""
        config = valid_config(temp_log_directory)
        config["LOG_EMAIL_NOTIFIER"]["ENABLE"] = True
        settings_manager.load(config)

        assert "fast_logging.E021" in error_ids(check_logging_settings({}))

    def test_email_settings_not_checked_when_notifier_disabled(
        self, temp_log_directory: str
    ) -> None:
        """Test that SMTP settings are not required while the notifier is off."""
        config = valid_config(temp_log_directory)
        config["LOG_EMAIL_NOTIFIER"]["ENABLE"] = False
        settings_manager.load(config)

        assert "fast_logging.E021" not in error_ids(check_logging_settings({}))

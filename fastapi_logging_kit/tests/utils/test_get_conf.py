import sys
from typing import Any, Dict

import pytest

from fastapi_logging_kit.settings import settings_manager
from fastapi_logging_kit.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON
from fastapi_logging_kit.utils.get_conf import (
    get_config,
    get_email_setting,
    get_log_dir_size_limit,
    include_log_iboard,
    is_auto_initialization_enabled,
    is_debug_enabled,
    is_initialization_message_enabled,
    is_log_sql_queries_enabled,
    use_email_notifier_template,
)

pytestmark = [
    pytest.mark.utils,
    pytest.mark.utils_get_conf,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


class TestGetConfig:
    """Test suite for the `get_config` accessor."""

    def test_returns_every_expected_key(self) -> None:
        """Test that the configuration mapping exposes every logging key."""
        config = get_config()
        assert set(config) == {
            "log_levels",
            "log_dir",
            "log_file_formats",
            "log_file_format_types",
            "extra_log_files",
            "console_level",
            "console_format",
            "colorize_console",
            "log_date_format",
            "log_email_notifier_enable",
            "log_email_notifier_log_levels",
            "log_email_notifier_log_format",
            "log_rotation",
            "log_rotation_overrides",
        }

    def test_reflects_the_defaults(self) -> None:
        """Test that the defaults are returned when nothing is configured."""
        config = get_config()
        assert config["log_levels"] == [
            "DEBUG",
            "INFO",
            "WARNING",
            "ERROR",
            "CRITICAL",
        ]
        assert config["console_level"] == "DEBUG"
        assert config["colorize_console"] is True
        assert config["log_email_notifier_enable"] is False
        assert config["log_email_notifier_log_levels"] == [None, None]
        assert config["log_rotation"]["TYPE"] == "none"
        assert config["log_rotation_overrides"] == {}

    def test_reflects_an_explicit_configuration(
        self, configure_settings: Dict[str, Any]
    ) -> None:
        """Test that an explicitly loaded configuration is returned.

        Args:
            configure_settings (Dict[str, Any]): The applied configuration.

        """
        config = get_config()
        assert config["log_levels"] == ["DEBUG", "INFO"]
        assert config["log_dir"] == "logs"
        assert config["log_email_notifier_enable"] is True
        assert config["log_email_notifier_log_levels"] == ["ERROR", None]
        assert config["log_email_notifier_log_format"] == 1


class TestBooleanAccessors:
    """Test suite for the boolean configuration accessors."""

    def test_defaults(self) -> None:
        """Test the values returned when nothing has been configured."""
        assert use_email_notifier_template() is True
        assert is_auto_initialization_enabled() is True
        assert is_initialization_message_enabled() is True
        assert is_log_sql_queries_enabled() is False
        assert include_log_iboard() is False
        assert is_debug_enabled() is False

    def test_explicit_configuration(self) -> None:
        """Test that each accessor reflects an explicit configuration."""
        settings_manager.load(
            {
                "AUTO_INITIALIZATION_ENABLE": False,
                "INITIALIZATION_MESSAGE_ENABLE": False,
                "LOG_SQL_QUERIES_ENABLE": True,
                "INCLUDE_LOG_iBOARD": True,
                "DEBUG": True,
                "LOG_EMAIL_NOTIFIER": {"ENABLE": True, "USE_TEMPLATE": False},
            }
        )
        assert use_email_notifier_template() is False
        assert is_auto_initialization_enabled() is False
        assert is_initialization_message_enabled() is False
        assert is_log_sql_queries_enabled() is True
        assert include_log_iboard() is True
        assert is_debug_enabled() is True


class TestGetLogDirSizeLimit:
    """Test suite for the `get_log_dir_size_limit` accessor."""

    def test_default_limit(self) -> None:
        """Test that the packaged default limit is returned."""
        assert get_log_dir_size_limit() == 1024

    def test_configured_limit(self, configure_settings: Dict[str, Any]) -> None:
        """Test that a configured limit is returned.

        Args:
            configure_settings (Dict[str, Any]): The applied configuration.

        """
        assert get_log_dir_size_limit() == 100


class TestGetEmailSetting:
    """Test suite for the `get_email_setting` accessor."""

    def test_returns_a_present_setting(
        self, configure_email_settings: Dict[str, Any]
    ) -> None:
        """Test that a configured SMTP setting is returned.

        Args:
            configure_email_settings (Dict[str, Any]): The email settings.

        """
        assert get_email_setting("EMAIL_HOST") == "smtp.example.com"
        assert get_email_setting("ADMIN_EMAIL") == "admin@example.com"

    def test_returns_none_for_a_missing_setting(
        self, configure_email_settings: Dict[str, Any]
    ) -> None:
        """Test that an absent setting resolves to None.

        Args:
            configure_email_settings (Dict[str, Any]): The email settings.

        """
        assert get_email_setting("EMAIL_TIMEOUT") is None

    def test_returns_the_supplied_default(self) -> None:
        """Test that the supplied default is returned when the key is absent."""
        assert get_email_setting("EMAIL_HOST", "fallback.example.com") == (
            "fallback.example.com"
        )

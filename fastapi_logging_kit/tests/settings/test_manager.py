import sys
from typing import Any, Dict

import pytest

from fastapi_logging_kit.constants import DefaultConsoleSettings, DefaultLoggingSettings
from fastapi_logging_kit.settings.manager import ENV_PREFIX, SettingsManager
from fastapi_logging_kit.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON

pytestmark = [
    pytest.mark.settings,
    pytest.mark.settings_manager,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


class TestSettingsManagerDefaults:
    """Test suite for the fallback to packaged defaults."""

    def test_core_defaults(self) -> None:
        """Test that an empty configuration resolves to the packaged defaults."""
        defaults = DefaultLoggingSettings()
        console_defaults = DefaultConsoleSettings()
        manager = SettingsManager()

        assert manager.log_dir == defaults.log_dir
        assert manager.log_levels == defaults.log_levels
        assert manager.log_file_formats == defaults.log_file_formats
        assert manager.log_file_format_types == defaults.log_file_format_types
        assert manager.extra_log_files == defaults.extra_log_files
        assert manager.log_date_format == defaults.log_date_format
        assert manager.console_level == console_defaults.log_console_level
        assert manager.console_format == console_defaults.log_console_format
        assert manager.colorize_console == console_defaults.log_console_colorize

    def test_flag_and_limit_defaults(self) -> None:
        """Test that the boolean flags and size limit fall back to defaults."""
        defaults = DefaultLoggingSettings()
        manager = SettingsManager()

        assert manager.auto_initialization_enabled == defaults.auto_initialization_enable
        assert (
            manager.initialization_message_enabled
            == defaults.initialization_message_enable
        )
        assert manager.log_sql_queries_enabled == defaults.log_sql_queries_enable
        assert manager.log_dir_size_limit == defaults.log_dir_size_limit
        assert manager.include_log_iboard == defaults.include_log_iboard
        assert manager.debug == defaults.debug

    def test_email_defaults(self) -> None:
        """Test that the email notifier defaults leave notifications disabled."""
        manager = SettingsManager()

        assert manager.email_notifier_enabled is False
        assert manager.email_notifier_log_levels == [None, None]
        assert manager.email_notifier_log_format == 1
        assert manager.use_email_notifier_template is True
        assert manager.email_settings == {}

    def test_rotation_defaults(self) -> None:
        """Test that rotation falls back to the packaged rotation defaults."""
        defaults = DefaultLoggingSettings()
        manager = SettingsManager()

        assert manager.log_rotation == dict(defaults.log_rotation)
        assert manager.log_rotation_overrides == defaults.log_rotation_overrides


class TestSettingsManagerExplicitMapping:
    """Test suite for configuration supplied as an explicit mapping."""

    def test_explicit_mapping_is_used(self, mock_settings: Dict[str, Any]) -> None:
        """Test that values from the supplied mapping are resolved."""
        manager = SettingsManager(mock_settings)

        assert manager.log_dir == "logs"
        assert manager.log_levels == ["DEBUG", "INFO"]
        assert manager.log_dir_size_limit == 100
        assert manager.debug is True

    def test_email_notifier_derived_values(
        self, mock_settings: Dict[str, Any]
    ) -> None:
        """Test that the notifier flags drive the derived level list."""
        manager = SettingsManager(mock_settings)

        assert manager.email_notifier_enabled is True
        assert manager.email_notifier_log_levels == ["ERROR", None]
        assert manager.email_notifier_log_format == 1
        assert manager.use_email_notifier_template is True

    def test_notify_critical_only(self) -> None:
        """Test that enabling only NOTIFY_CRITICAL yields the CRITICAL level."""
        manager = SettingsManager(
            {"LOG_EMAIL_NOTIFIER": {"NOTIFY_ERROR": False, "NOTIFY_CRITICAL": True}}
        )
        assert manager.email_notifier_log_levels == [None, "CRITICAL"]

    def test_both_notify_flags_enabled(self) -> None:
        """Test that both notify flags produce both notifier levels."""
        manager = SettingsManager(
            {"LOG_EMAIL_NOTIFIER": {"NOTIFY_ERROR": True, "NOTIFY_CRITICAL": True}}
        )
        assert manager.email_notifier_log_levels == ["ERROR", "CRITICAL"]

    def test_email_block_is_read(self, email_mock_settings: Dict[str, Any]) -> None:
        """Test that SMTP settings are read from the EMAIL config key."""
        manager = SettingsManager({"EMAIL": email_mock_settings})
        assert manager.email_settings == email_mock_settings

    def test_non_mapping_raises_value_error(self) -> None:
        """Test that a non-mapping configuration raises ValueError."""
        with pytest.raises(ValueError, match="must be a dictionary"):
            SettingsManager(["not", "a", "mapping"])  # type: ignore[arg-type]

    def test_load_none_falls_back_to_defaults(
        self, mock_settings: Dict[str, Any]
    ) -> None:
        """Test that ``load(None)`` discards the previous explicit mapping."""
        manager = SettingsManager(mock_settings)
        assert manager.log_dir == "logs"

        manager.load(None)
        assert manager.log_dir == DefaultLoggingSettings().log_dir

    def test_configure_replaces_configuration(self) -> None:
        """Test that ``configure`` applies keyword arguments as configuration."""
        manager = SettingsManager()
        manager.configure(LOG_DIR="/var/log/app", LOG_FILE_LEVELS=["ERROR"])

        assert manager.log_dir == "/var/log/app"
        assert manager.log_levels == ["ERROR"]

    def test_reset_discards_explicit_configuration(self) -> None:
        """Test that ``reset`` drops the explicit mapping."""
        manager = SettingsManager({"LOG_DIR": "/custom"})
        assert manager.log_dir == "/custom"

        manager.reset()
        assert manager.log_dir == DefaultLoggingSettings().log_dir

    def test_get_returns_default_for_missing_key(self) -> None:
        """Test that ``get`` returns the default when the key is absent."""
        manager = SettingsManager({"LOG_DIR": "/custom"})

        assert manager.get("LOG_DIR", "fallback") == "/custom"
        assert manager.get("NOT_A_KEY", "fallback") == "fallback"


class TestSettingsManagerEnvironment:
    """Test suite for configuration read from environment variables."""

    def test_environment_prefix_uses_public_package_identity(self) -> None:
        """Test that legacy environment settings use the new package prefix."""
        assert ENV_PREFIX == "FASTAPI_LOGGING_"

    def test_env_value_parsed_as_json(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that JSON-parseable environment values are decoded."""
        monkeypatch.setenv(f"{ENV_PREFIX}LOG_FILE_LEVELS", '["INFO", "ERROR"]')
        monkeypatch.setenv(f"{ENV_PREFIX}LOG_DIR_SIZE_LIMIT", "42")

        manager = SettingsManager()
        assert manager.log_levels == ["INFO", "ERROR"]
        assert manager.log_dir_size_limit == 42

    def test_env_value_falls_back_to_plain_string(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that a value which is not valid JSON is kept as a string."""
        monkeypatch.setenv(f"{ENV_PREFIX}LOG_DIR", "/var/log/app")

        manager = SettingsManager()
        assert manager.log_dir == "/var/log/app"

    def test_unprefixed_env_variables_are_ignored(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that environment variables without the prefix are skipped."""
        monkeypatch.setenv("LOG_DIR", "/should/be/ignored")

        manager = SettingsManager()
        assert "LOG_DIR" not in manager.log_settings
        assert manager.log_dir == DefaultLoggingSettings().log_dir

    def test_explicit_mapping_wins_over_environment(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that an explicit mapping takes priority over the environment."""
        monkeypatch.setenv(f"{ENV_PREFIX}LOG_DIR", "/from/env")

        manager = SettingsManager({"LOG_DIR": "/from/mapping"})
        assert manager.log_dir == "/from/mapping"

    def test_environment_used_when_mapping_omits_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that the environment supplies keys the mapping does not set."""
        monkeypatch.setenv(f"{ENV_PREFIX}LOG_DIR", "/from/env")

        manager = SettingsManager({"LOG_FILE_LEVELS": ["ERROR"]})
        assert manager.log_dir == "/from/env"
        assert manager.log_levels == ["ERROR"]


class TestSettingsManagerRotation:
    """Test suite for the LOG_ROTATION merging behaviour."""

    def test_user_rotation_merges_over_defaults(self) -> None:
        """Test that a partial LOG_ROTATION merges on top of the defaults."""
        manager = SettingsManager({"LOG_ROTATION": {"TYPE": "size", "COMPRESS": True}})

        assert manager.log_rotation["TYPE"] == "size"
        assert manager.log_rotation["COMPRESS"] is True
        # untouched keys keep their default values
        assert manager.log_rotation["BACKUP_COUNT"] == 5
        assert manager.log_rotation["MAX_BYTES"] == 10_485_760

    def test_non_dict_rotation_leaves_defaults_intact(self) -> None:
        """Test that a non-dict LOG_ROTATION value is ignored."""
        manager = SettingsManager({"LOG_ROTATION": "not-a-dict"})

        assert manager.log_rotation == dict(DefaultLoggingSettings().log_rotation)

    def test_rotation_overrides_are_read(self) -> None:
        """Test that LOG_ROTATION_OVERRIDES is resolved from the mapping."""
        overrides = {"ERROR": {"TYPE": "time", "WHEN": "midnight"}}
        manager = SettingsManager({"LOG_ROTATION_OVERRIDES": overrides})

        assert manager.log_rotation_overrides == overrides

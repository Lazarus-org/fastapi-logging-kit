from typing import Any, Dict

from fast_logging.settings import settings_manager


def get_config() -> Dict:
    """Retrieve logging configuration from the SettingsManager.

    Returns:
        Dict: A dictionary containing all necessary configurations for logging.

    """
    config = {
        "log_levels": settings_manager.log_levels,
        "log_dir": settings_manager.log_dir,
        "log_file_formats": settings_manager.log_file_formats,
        "log_file_format_types": settings_manager.log_file_format_types,
        "extra_log_files": settings_manager.extra_log_files,
        "console_level": settings_manager.console_level,
        "console_format": settings_manager.console_format,
        "colorize_console": settings_manager.colorize_console,
        "log_date_format": settings_manager.log_date_format,
        "log_email_notifier_enable": settings_manager.email_notifier_enabled,
        "log_email_notifier_log_levels": settings_manager.email_notifier_log_levels,
        "log_email_notifier_log_format": settings_manager.email_notifier_log_format,
        "log_rotation": settings_manager.log_rotation,
        "log_rotation_overrides": settings_manager.log_rotation_overrides,
    }

    return config


def use_email_notifier_template() -> bool:
    """Check whether the email notifier should use a template.

    Returns:
        bool: True if the email notifier should use a template, False otherwise.

    """
    return settings_manager.use_email_notifier_template


def is_auto_initialization_enabled() -> bool:
    """Check if the AUTO_INITIALIZATION_ENABLE for the logging system is set to
    True.

    Returns:
        bool: True if AUTO_INITIALIZATION_ENABLE, False otherwise. Defaults to True if not specified.

    """
    return settings_manager.auto_initialization_enabled


def is_initialization_message_enabled() -> bool:
    """Check if the INITIALIZATION_MESSAGE_ENABLE is set to True.

    Returns:
        bool: True if INITIALIZATION_MESSAGE_ENABLE is True, False otherwise.

    """
    return settings_manager.initialization_message_enabled


def is_log_sql_queries_enabled() -> bool:
    """Check if the LOG_SQL_QUERIES_ENABLE for the logging system is set to
    True.

    Returns:
        bool: True if LOG_SQL_QUERIES_ENABLE, False otherwise.

    """
    return settings_manager.log_sql_queries_enabled


def get_log_dir_size_limit() -> int:
    """Check for the LOG_DIR_SIZE_LIMIT for managing the log directory size.

    Returns:
        int: the limit of log directory size in MB. Defaults to 1024 MB if not specified.

    """
    return settings_manager.log_dir_size_limit


def include_log_iboard() -> bool:
    """Check if the INCLUDE_LOG_iBOARD for the logging system is set to True.

    Returns:
        bool: True if INCLUDE_LOG_iBOARD, False otherwise.

    """
    return settings_manager.include_log_iboard


def is_debug_enabled() -> bool:
    """Check whether the application is configured to run in debug mode.

    ``django_logging`` read ``settings.DEBUG`` to decide whether query
    tracking should be active. FastAPI has no such global, so the flag
    is read from the ``DEBUG`` key of the ``fast_logging``
    configuration instead.

    Returns:
        bool: True if DEBUG is enabled, False otherwise.

    """
    return settings_manager.debug


def get_email_setting(name: str, default: Any = None) -> Any:
    """Return a single SMTP setting from the ``EMAIL`` configuration block.

    Args:
        name (str): The setting name, e.g. ``EMAIL_HOST`` or ``ADMIN_EMAIL``.
        default (Any): The value returned when the setting is absent.

    Returns:
        Any: The configured value or ``default``.

    """
    return settings_manager.email_settings.get(name, default)  # type: ignore[attr-defined]

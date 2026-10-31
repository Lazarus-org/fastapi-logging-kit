import os
from typing import Any, Dict, Iterator

import pytest

from fastapi_logging_kit.cache import cache
from fastapi_logging_kit.checks import registry
from fastapi_logging_kit.contextvar import manager
from fastapi_logging_kit.settings import ENV_PREFIX, settings_manager
from fastapi_logging_kit.utils.sql import clear_queries


@pytest.fixture(autouse=True)
def reset_settings() -> Iterator[None]:
    """Restore global state after every test.

    ``settings_manager``, the context variables, the cache and the SQL
    query log are all process-global, so each test gets them reset. This
    replaces the ``override_settings`` juggling the Django suite needed.

    Yields:
        None

    """
    original_environ = {
        key: value
        for key, value in os.environ.items()
        if key.startswith(ENV_PREFIX)
    }

    yield

    for key in [k for k in os.environ if k.startswith(ENV_PREFIX)]:
        del os.environ[key]
    os.environ.update(original_environ)

    settings_manager.reset()
    manager.clear()
    clear_queries()
    cache.clear()


@pytest.fixture
def mock_settings() -> Dict[str, Any]:
    """Return a complete configuration mapping for the logging system.

    Returns:
        Dict[str, Any]: A configuration covering every supported key.

    """
    return {
        "AUTO_INITIALIZATION_ENABLE": True,
        "INITIALIZATION_MESSAGE_ENABLE": False,
        "LOG_FILE_LEVELS": ["DEBUG", "INFO"],
        "LOG_DIR": "logs",
        "LOG_FILE_FORMATS": {"DEBUG": 1, "INFO": 1},
        "LOG_FILE_FORMAT_TYPES": {"DEBUG": "normal", "INFO": "normal"},
        "EXTRA_LOG_FILES": {"DEBUG": False, "INFO": False},
        "LOG_CONSOLE_LEVEL": "DEBUG",
        "LOG_CONSOLE_FORMAT": 1,
        "LOG_CONSOLE_COLORIZE": True,
        "LOG_DATE_FORMAT": "%Y-%m-%d %H:%M:%S",
        "LOG_EMAIL_NOTIFIER": {
            "ENABLE": True,
            "NOTIFY_ERROR": True,
            "NOTIFY_CRITICAL": False,
            "LOG_FORMAT": 1,
            "USE_TEMPLATE": True,
        },
        "LOG_SQL_QUERIES_ENABLE": True,
        "LOG_DIR_SIZE_LIMIT": 100,
        "INCLUDE_LOG_iBOARD": False,
        "DEBUG": True,
    }


@pytest.fixture
def configure_settings(mock_settings: Dict[str, Any]) -> Dict[str, Any]:
    """Apply ``mock_settings`` to the settings manager.

    Args:
        mock_settings (Dict[str, Any]): The configuration to apply.

    Returns:
        Dict[str, Any]: The applied configuration.

    """
    settings_manager.load(mock_settings)
    return mock_settings


@pytest.fixture
def email_mock_settings() -> Dict[str, Any]:
    """Return an ``EMAIL`` configuration block with every SMTP setting.

    Returns:
        Dict[str, Any]: The email settings.

    """
    return {
        "EMAIL_HOST": "smtp.example.com",
        "EMAIL_PORT": 587,
        "EMAIL_HOST_USER": "user@example.com",
        "EMAIL_HOST_PASSWORD": "password",
        "EMAIL_USE_TLS": True,
        "DEFAULT_FROM_EMAIL": "noreply@example.com",
    }


@pytest.fixture
def admin_email_mock_settings(email_mock_settings: Dict[str, Any]) -> Dict[str, Any]:
    """Return the SMTP settings plus ``ADMIN_EMAIL``.

    Args:
        email_mock_settings (Dict[str, Any]): The base SMTP settings.

    Returns:
        Dict[str, Any]: The email settings including ADMIN_EMAIL.

    """
    return {**email_mock_settings, "ADMIN_EMAIL": "admin@example.com"}


@pytest.fixture
def configure_email_settings(
    admin_email_mock_settings: Dict[str, Any]
) -> Dict[str, Any]:
    """Load the full email settings into the settings manager.

    Args:
        admin_email_mock_settings (Dict[str, Any]): The email settings.

    Returns:
        Dict[str, Any]: The applied email settings.

    """
    settings_manager.load({"EMAIL": admin_email_mock_settings})
    return admin_email_mock_settings


@pytest.fixture
def clean_check_registry() -> Iterator[list]:
    """Snapshot and restore the check registry.

    Yields:
        list: The live registry, restored to its original contents
        afterwards.

    """
    original = list(registry)
    yield registry
    registry.clear()
    registry.extend(original)

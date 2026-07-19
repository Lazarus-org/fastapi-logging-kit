import logging
from typing import Any, Iterator
from unittest.mock import ANY, MagicMock, patch

import pytest

from fast_logging.handlers import EmailHandler


@pytest.fixture
def email_handler() -> EmailHandler:
    """Return an EmailHandler with a plain formatter attached.

    Returns:
        EmailHandler: The handler.

    """
    handler = EmailHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s | %(message)s"))
    return handler


@pytest.fixture
def mock_smtp() -> Iterator[MagicMock]:
    """Patch ``smtplib.SMTP`` as used by the notifier.

    Yields:
        MagicMock: The patched SMTP class.

    """
    with patch("fast_logging.utils.log_email_notifier.notifier.SMTP") as mock:
        yield mock


@pytest.fixture
def mock_send_email_async() -> Iterator[MagicMock]:
    """Patch ``send_email_async`` as imported by the email handler.

    Yields:
        MagicMock: The patched function.

    """
    with patch("fast_logging.handlers.email_handler.send_email_async") as mock:
        yield mock


@pytest.fixture
def mock_logger() -> MagicMock:
    """Return a Mock standing in for a logger.

    Returns:
        MagicMock: The mock logger.

    """
    return MagicMock(spec=logging.Logger)


@pytest.fixture
def magic_mock_logger() -> MagicMock:
    """Return an unrestricted MagicMock logger.

    Returns:
        MagicMock: The mock logger.

    """
    return MagicMock()


@pytest.fixture
def notifier_mock_logger() -> Iterator[MagicMock]:
    """Patch the notifier module's logger.

    Yields:
        MagicMock: The patched logger.

    """
    with patch("fast_logging.utils.log_email_notifier.notifier.logger") as mock:
        yield mock


@pytest.fixture
def any_arg() -> Any:
    """Return ``unittest.mock.ANY`` for argument assertions.

    Returns:
        Any: The ANY sentinel.

    """
    return ANY

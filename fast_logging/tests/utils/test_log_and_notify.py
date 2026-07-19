import logging
import sys
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from fast_logging.settings import settings_manager
from fast_logging.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON
from fast_logging.utils.log_email_notifier.log_and_notify import log_and_notify_admin

pytestmark = [
    pytest.mark.utils,
    pytest.mark.utils_log_and_notify,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


class TestLogAndNotifyAdmin:
    """Test suite for :func:`log_and_notify_admin`."""

    def test_raises_when_notifier_disabled(self, mock_logger: MagicMock) -> None:
        """Test that a disabled email notifier is rejected with a
        ValueError."""
        settings_manager.load({"LOG_EMAIL_NOTIFIER": {"ENABLE": False}})

        with pytest.raises(ValueError, match="Email notifier is disabled"):
            log_and_notify_admin(mock_logger, logging.ERROR, "boom")

    def test_sends_email_on_success(
        self, admin_email_mock_settings: Dict[str, Any]
    ) -> None:
        """Test that an enabled notifier logs the record and emails the
        admin."""
        settings_manager.load(
            {
                "EMAIL": admin_email_mock_settings,
                "LOG_EMAIL_NOTIFIER": {
                    "ENABLE": True,
                    "LOG_FORMAT": "%(levelname)s | %(message)s",
                },
            }
        )
        logger = logging.getLogger("test_log_and_notify")

        with patch(
            "fast_logging.utils.log_email_notifier.log_and_notify.send_email_async"
        ) as mock_send:
            log_and_notify_admin(logger, logging.ERROR, "something broke")

        mock_send.assert_called_once()
        subject, body, recipients = mock_send.call_args[0]
        assert subject == "New Log Record: ERROR"
        assert recipients == ["admin@example.com"]
        assert "something broke" in body

    def test_sends_email_with_default_context_format(
        self, admin_email_mock_settings: Dict[str, Any]
    ) -> None:
        """Test that the default LOG_FORMAT, which references %(context)s,
        formats successfully.

        The record never passes through a handler's filters, so
        ``log_and_notify_admin`` has to populate ``record.context``
        itself; without that the format call raises "Formatting field not
        found in record: 'context'".

        """
        settings_manager.load(
            {
                "EMAIL": admin_email_mock_settings,
                "LOG_EMAIL_NOTIFIER": {"ENABLE": True},  # LOG_FORMAT defaults to 1
            }
        )
        logger = logging.getLogger("test_log_and_notify_default_format")

        with patch(
            "fast_logging.utils.log_email_notifier.log_and_notify.send_email_async"
        ) as mock_send:
            log_and_notify_admin(logger, logging.ERROR, "context aware")

        mock_send.assert_called_once()
        assert "context aware" in mock_send.call_args[0][1]

    def test_passes_request_from_extra(
        self, admin_email_mock_settings: Dict[str, Any], request_factory: Any
    ) -> None:
        """Test that a request supplied via extra enriches the email body."""
        settings_manager.load(
            {
                "EMAIL": admin_email_mock_settings,
                "LOG_EMAIL_NOTIFIER": {
                    "ENABLE": True,
                    "LOG_FORMAT": "%(levelname)s | %(message)s",
                },
            }
        )
        logger = logging.getLogger("test_log_and_notify_request")
        request = request_factory(headers={"user-agent": "TestBrowser/2.0"})

        with patch(
            "fast_logging.utils.log_email_notifier.log_and_notify.send_email_async"
        ) as mock_send:
            log_and_notify_admin(
                logger, logging.ERROR, "with request", extra={"request": request}
            )

        _subject, body, _recipients = mock_send.call_args[0]
        assert "TestBrowser/2.0" in body

    def test_raises_when_record_creation_fails(
        self, admin_email_mock_settings: Dict[str, Any], mock_logger: MagicMock
    ) -> None:
        """Test that a bad parameter raises a ValueError about the invalid
        param."""
        settings_manager.load(
            {
                "EMAIL": admin_email_mock_settings,
                "LOG_EMAIL_NOTIFIER": {
                    "ENABLE": True,
                    "LOG_FORMAT": "%(levelname)s | %(message)s",
                },
            }
        )
        mock_logger.makeRecord.side_effect = TypeError("bad param")

        with pytest.raises(ValueError, match="Failed to log message due to invalid"):
            log_and_notify_admin(mock_logger, logging.ERROR, "boom")

    def test_raises_when_admin_email_missing(
        self, email_mock_settings: Dict[str, Any]
    ) -> None:
        """Test that a missing ADMIN_EMAIL is reported as a ValueError."""
        settings_manager.load(
            {
                "EMAIL": email_mock_settings,
                "LOG_EMAIL_NOTIFIER": {
                    "ENABLE": True,
                    "LOG_FORMAT": "%(levelname)s | %(message)s",
                },
            }
        )
        logger = logging.getLogger("test_log_and_notify_no_admin")

        with pytest.raises(ValueError, match="'ADMIN EMAIL' not provided"):
            log_and_notify_admin(logger, logging.ERROR, "boom")

import sys
import threading
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

from fastapi_logging_kit.settings import settings_manager
from fastapi_logging_kit.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON
from fastapi_logging_kit.utils.log_email_notifier.notifier import (
    send_email_async,
    send_email_with_attachment,
)

pytestmark = [
    pytest.mark.utils,
    pytest.mark.utils_email_notifier,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


class TestSendEmailAsync:
    """Test suite for :func:`send_email_async`."""

    def test_sends_via_configured_smtp_server(
        self,
        configure_email_settings: Dict[str, Any],
        mock_smtp: MagicMock,
        notifier_mock_logger: MagicMock,
    ) -> None:
        """Test that the worker thread delivers the message over SMTP."""
        event = threading.Event()

        send_email_async("Subject", "<p>body</p>", ["admin@example.com"], event)
        assert event.wait(timeout=5)

        mock_smtp.assert_called_once_with("smtp.example.com", 587, timeout=10)
        server = mock_smtp.return_value
        server.starttls.assert_called_once()
        server.login.assert_called_once_with("user@example.com", "password")
        server.sendmail.assert_called_once()
        from_email, recipients, message = server.sendmail.call_args[0]
        assert from_email == "noreply@example.com"
        assert recipients == ["admin@example.com"]
        assert "Subject: Subject" in message
        server.quit.assert_called_once()
        notifier_mock_logger.info.assert_called_once()

    def test_skips_starttls_when_tls_disabled(
        self,
        admin_email_mock_settings: Dict[str, Any],
        mock_smtp: MagicMock,
        notifier_mock_logger: MagicMock,
    ) -> None:
        """Test that starttls is not called when EMAIL_USE_TLS is False."""
        settings_manager.load(
            {"EMAIL": {**admin_email_mock_settings, "EMAIL_USE_TLS": False}}
        )
        event = threading.Event()

        send_email_async("Subject", "body", ["admin@example.com"], event)
        assert event.wait(timeout=5)

        mock_smtp.return_value.starttls.assert_not_called()
        mock_smtp.return_value.sendmail.assert_called_once()

    def test_logs_warning_when_delivery_fails(
        self,
        configure_email_settings: Dict[str, Any],
        mock_smtp: MagicMock,
        notifier_mock_logger: MagicMock,
    ) -> None:
        """Test that a delivery failure is swallowed and logged as a
        warning."""
        mock_smtp.side_effect = OSError("connection refused")
        event = threading.Event()

        send_email_async("Subject", "body", ["admin@example.com"], event)
        assert event.wait(timeout=5)

        notifier_mock_logger.warning.assert_called_once()
        assert "connection refused" in str(notifier_mock_logger.warning.call_args)
        notifier_mock_logger.info.assert_not_called()

    def test_runs_without_an_event(
        self,
        configure_email_settings: Dict[str, Any],
        mock_smtp: MagicMock,
        notifier_mock_logger: MagicMock,
    ) -> None:
        """Test that omitting the event argument still delivers the mail."""
        send_email_async("Subject", "body", ["admin@example.com"])

        for thread in threading.enumerate():
            if thread is not threading.current_thread():
                thread.join(timeout=5)

        mock_smtp.return_value.sendmail.assert_called_once()


class TestSendEmailWithAttachment:
    """Test suite for :func:`send_email_with_attachment`."""

    def test_attaches_the_file_and_delivers(
        self,
        configure_email_settings: Dict[str, Any],
        mock_smtp: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that the file is attached and the message handed to SMTP."""
        attachment = tmp_path / "logs.zip"
        attachment.write_bytes(b"zipped-logs")

        send_email_with_attachment(
            "Logs", "see attached", ["admin@example.com"], str(attachment)
        )

        server = mock_smtp.return_value
        server.sendmail.assert_called_once()
        from_email, recipients, message = server.sendmail.call_args[0]
        assert from_email == "noreply@example.com"
        assert recipients == ["admin@example.com"]
        assert "Subject: Logs" in message
        assert "see attached" in message
        assert 'filename="logs.zip"' in message
        server.quit.assert_called_once()

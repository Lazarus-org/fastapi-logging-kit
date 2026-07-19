import logging
import sys
from datetime import datetime
from typing import Any, Callable, Dict
from unittest.mock import MagicMock, patch

import pytest

from fast_logging.handlers import EmailHandler
from fast_logging.settings import settings_manager
from fast_logging.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON

pytestmark = [
    pytest.mark.handlers,
    pytest.mark.email_handler,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


class TestEmailHandlerEmit:
    """Test suite for :meth:`EmailHandler.emit`."""

    def test_emit_with_template(
        self,
        email_handler: EmailHandler,
        error_log_record: logging.LogRecord,
        admin_email_mock_settings: Dict[str, Any],
        mock_send_email_async: MagicMock,
    ) -> None:
        """Test that emit renders the template when USE_TEMPLATE is on."""
        settings_manager.load(
            {
                "EMAIL": admin_email_mock_settings,
                "LOG_EMAIL_NOTIFIER": {"ENABLE": True, "USE_TEMPLATE": True},
            }
        )

        email_handler.emit(error_log_record)

        mock_send_email_async.assert_called_once()
        subject, body, recipients = mock_send_email_async.call_args[0]
        assert subject == "New Log Record: ERROR"
        assert recipients == ["admin@example.com"]
        assert "<html" in body
        assert "This is an error message" in body

    def test_emit_without_template(
        self,
        email_handler: EmailHandler,
        error_log_record: logging.LogRecord,
        admin_email_mock_settings: Dict[str, Any],
        mock_send_email_async: MagicMock,
    ) -> None:
        """Test that emit sends the raw formatted entry when templating is
        off."""
        settings_manager.load(
            {
                "EMAIL": admin_email_mock_settings,
                "LOG_EMAIL_NOTIFIER": {"ENABLE": True, "USE_TEMPLATE": False},
            }
        )

        email_handler.emit(error_log_record)

        _subject, body, _recipients = mock_send_email_async.call_args[0]
        assert body == "ERROR | This is an error message"

    def test_emit_calls_handle_error_on_failure(
        self,
        email_handler: EmailHandler,
        error_log_record: logging.LogRecord,
        configure_email_settings: Dict[str, Any],
    ) -> None:
        """Test that emit routes any exception through handleError."""
        with patch.object(
            email_handler, "format", side_effect=ValueError("boom")
        ), patch.object(email_handler, "handleError") as mock_handle_error:
            email_handler.emit(error_log_record)

        mock_handle_error.assert_called_once_with(error_log_record)

    def test_emit_calls_handle_error_when_sending_fails(
        self,
        email_handler: EmailHandler,
        error_log_record: logging.LogRecord,
        configure_email_settings: Dict[str, Any],
        mock_send_email_async: MagicMock,
    ) -> None:
        """Test that a failure inside send_email_async reaches handleError."""
        mock_send_email_async.side_effect = RuntimeError("smtp down")

        with patch.object(email_handler, "handleError") as mock_handle_error:
            email_handler.emit(error_log_record)

        mock_handle_error.assert_called_once_with(error_log_record)


class TestEmailHandlerRenderTemplate:
    """Test suite for :meth:`EmailHandler.render_template`."""

    def test_render_without_request(self) -> None:
        """Test that missing request details hide the IP and browser blocks."""
        body = EmailHandler.render_template("a log entry")

        assert "a log entry" in body
        assert "IP Address:" not in body
        assert "Browser Type:" not in body

    def test_render_with_request(
        self, request_factory: Callable[..., Any]
    ) -> None:
        """Test that a request contributes its IP address and user agent."""
        request = request_factory(
            headers={"user-agent": "TestBrowser/1.0", "x-forwarded-for": "10.0.0.7"}
        )

        body = EmailHandler.render_template("a log entry", request)

        assert "IP Address:" in body
        assert "10.0.0.7" in body
        assert "Browser Type:" in body
        assert "TestBrowser/1.0" in body

    def test_render_includes_formatted_date_and_time(self) -> None:
        """Test that the rendered body carries the uppercased date and the
        time."""
        now = datetime.now().astimezone()
        expected_date = now.strftime("%d %B %Y").replace(
            now.strftime("%B"), now.strftime("%B").upper()
        )

        body = EmailHandler.render_template("a log entry")

        assert expected_date in body
        assert "Email prepared at" in body
        assert now.strftime("%I:%M %p") in body

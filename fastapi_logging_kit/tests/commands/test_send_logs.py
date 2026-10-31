import os
import sys
from typing import Any, Dict
from unittest.mock import patch

import pytest

from fastapi_logging_kit.commands.send_logs import Command, run
from fastapi_logging_kit.exceptions import ImproperlyConfigured
from fastapi_logging_kit.settings import settings_manager
from fastapi_logging_kit.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON

pytestmark = [
    pytest.mark.commands,
    pytest.mark.commands_send_logs,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


class TestSendLogsCommand:
    """Test suite for the `send_logs` command."""

    def test_missing_log_directory(self, tmp_path: Any) -> None:
        """Test that a missing log directory reports an error and stops."""
        missing = str(tmp_path / "nope")
        settings_manager.load({"LOG_DIR": missing})

        out = run(echo=False, email="ops@example.com")

        assert "does not exist" in out.getvalue()

    def test_missing_email_settings_raise(self, temp_log_directory: str) -> None:
        """Test that absent email settings raise ImproperlyConfigured."""
        settings_manager.load({"LOG_DIR": temp_log_directory})

        with pytest.raises(ImproperlyConfigured):
            run(echo=False, email="ops@example.com")

    def test_sends_logs_successfully(
        self, temp_log_directory: str, email_mock_settings: Dict[str, Any]
    ) -> None:
        """Test the happy path where the zipped logs are emailed."""
        settings_manager.load(
            {"LOG_DIR": temp_log_directory, "EMAIL": email_mock_settings}
        )

        with patch(
            "fastapi_logging_kit.commands.send_logs.send_email_with_attachment"
        ) as mock_send:
            out = run(echo=False, email="ops@example.com")

        mock_send.assert_called_once()
        zip_path = mock_send.call_args.kwargs["attachment_path"]
        assert mock_send.call_args.kwargs["recipient_list"] == ["ops@example.com"]
        assert "Logs sent successfully to ops@example.com." in out.getvalue()
        assert not os.path.exists(zip_path)

    def test_reports_send_failure(
        self, temp_log_directory: str, email_mock_settings: Dict[str, Any]
    ) -> None:
        """Test that a failure while sending is reported and cleaned up."""
        settings_manager.load(
            {"LOG_DIR": temp_log_directory, "EMAIL": email_mock_settings}
        )

        with patch(
            "fastapi_logging_kit.commands.send_logs.send_email_with_attachment",
            side_effect=Exception("smtp down"),
        ) as mock_send:
            out = run(echo=False, email="ops@example.com")

        zip_path = mock_send.call_args.kwargs["attachment_path"]
        assert "Failed to send logs: smtp down" in out.getvalue()
        assert not os.path.exists(zip_path)


class TestValidateEmailSettings:
    """Test suite for `Command.validate_email_settings`."""

    def test_passes_with_full_settings(
        self, email_mock_settings: Dict[str, Any]
    ) -> None:
        """Test that complete SMTP settings validate without raising."""
        settings_manager.load({"EMAIL": email_mock_settings})

        assert Command.validate_email_settings() is None

    def test_raises_when_admin_email_required(
        self, email_mock_settings: Dict[str, Any]
    ) -> None:
        """Test that a missing ADMIN_EMAIL raises when it is required."""
        settings_manager.load({"EMAIL": email_mock_settings})

        with pytest.raises(ImproperlyConfigured):
            Command.validate_email_settings(require_admin_email=True)

import os
import sys
from typing import Any, Dict
from unittest.mock import patch

import pytest

from fast_logging.commands.logs_size_audit import Command, run
from fast_logging.exceptions import ImproperlyConfigured
from fast_logging.settings import settings_manager
from fast_logging.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON

pytestmark = [
    pytest.mark.commands,
    pytest.mark.commands_logs_size_audit,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


class TestLogsSizeAuditCommand:
    """Test suite for the `logs_size_audit` command."""

    def test_missing_log_directory(self, tmp_path: Any) -> None:
        """Test that a missing log directory reports an error and stops."""
        missing = str(tmp_path / "nope")
        settings_manager.load({"LOG_DIR": missing})

        out = run(echo=False)

        assert f"Log directory not found: {missing}" in out.getvalue()

    def test_size_under_limit(self, log_dir_with_rotated_files: str) -> None:
        """Test that a small log directory reports being under the limit."""
        settings_manager.load(
            {"LOG_DIR": log_dir_with_rotated_files, "LOG_DIR_SIZE_LIMIT": 100}
        )

        out = run(echo=False)
        output = out.getvalue()

        assert "Log directory size is under the limit" in output
        assert "Log directory size breakdown:" in output
        assert "TOTAL" in output

    def test_size_over_limit_sends_email_with_template(
        self, log_dir_with_rotated_files: str, admin_email_mock_settings: Dict[str, Any]
    ) -> None:
        """Test that exceeding the limit sends a templated warning email."""
        settings_manager.load(
            {
                "LOG_DIR": log_dir_with_rotated_files,
                "LOG_DIR_SIZE_LIMIT": 0,
                "EMAIL": admin_email_mock_settings,
                "LOG_EMAIL_NOTIFIER": {"USE_TEMPLATE": True},
            }
        )

        with patch(
            "fast_logging.commands.logs_size_audit.send_email_async"
        ) as mock_send:
            out = run(echo=False)

        mock_send.assert_called_once()
        assert mock_send.call_args.kwargs["recipient_list"] == ["admin@example.com"]
        assert "Warning email sent successfully." in out.getvalue()

    def test_size_over_limit_sends_plain_email(
        self, log_dir_with_rotated_files: str, admin_email_mock_settings: Dict[str, Any]
    ) -> None:
        """Test that the raw message is sent when templating is disabled."""
        settings_manager.load(
            {
                "LOG_DIR": log_dir_with_rotated_files,
                "LOG_DIR_SIZE_LIMIT": 0,
                "EMAIL": admin_email_mock_settings,
                "LOG_EMAIL_NOTIFIER": {"USE_TEMPLATE": False},
            }
        )

        with patch(
            "fast_logging.commands.logs_size_audit.send_email_async"
        ) as mock_send:
            run(echo=False)

        body = mock_send.call_args.kwargs["body"]
        assert body.startswith("The size of the log files has exceeded 0 MB.")
        assert "Breakdown:" in body

    def test_size_over_limit_requires_email_settings(
        self, log_dir_with_rotated_files: str
    ) -> None:
        """Test that missing email settings raise before any email is sent."""
        settings_manager.load(
            {"LOG_DIR": log_dir_with_rotated_files, "LOG_DIR_SIZE_LIMIT": 0}
        )

        with pytest.raises(ImproperlyConfigured):
            run(echo=False)


class TestCategorizeFiles:
    """Test suite for `Command._categorize_files`."""

    def test_buckets_every_file_type(self, temp_log_directory: str) -> None:
        """Test that files land in the active, rotated, archived and compressed buckets."""
        archive_dir = os.path.join(temp_log_directory, "archive")
        os.makedirs(archive_dir, exist_ok=True)

        for path in (
            os.path.join(temp_log_directory, "info.log"),
            os.path.join(temp_log_directory, "info.log.1"),
            os.path.join(temp_log_directory, "debug.log.1.gz"),
            os.path.join(archive_dir, "old.log.2"),
        ):
            with open(path, "wb") as file:
                file.write(b"data\n")

        breakdown = Command(echo=False)._categorize_files(temp_log_directory)

        assert [os.path.basename(p) for p in breakdown["active"][0]] == ["info.log"]
        assert [os.path.basename(p) for p in breakdown["rotated"][0]] == ["info.log.1"]
        assert [os.path.basename(p) for p in breakdown["compressed"][0]] == [
            "debug.log.1.gz"
        ]
        assert [os.path.basename(p) for p in breakdown["archived"][0]] == ["old.log.2"]
        assert all(size > 0 for _, size in breakdown.values())

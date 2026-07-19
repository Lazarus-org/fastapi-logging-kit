import sys
from typing import Any, Dict

import pytest

from fast_logging.settings import settings_manager
from fast_logging.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON
from fast_logging.validators.email_settings_validator import check_email_settings

pytestmark = [
    pytest.mark.validators,
    pytest.mark.email_settings_validator,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


class TestCheckEmailSettings:
    """Test suite for `check_email_settings`."""

    def test_complete_settings_report_no_errors(
        self, configure_email_settings: Dict[str, Any]
    ) -> None:
        """Test that a complete EMAIL block including ADMIN_EMAIL is accepted."""
        assert check_email_settings() == []

    def test_admin_email_not_required(
        self, email_mock_settings: Dict[str, Any]
    ) -> None:
        """Test that ADMIN_EMAIL may be absent when it is not required."""
        settings_manager.load({"EMAIL": email_mock_settings})

        assert check_email_settings(require_admin_email=False) == []

    def test_missing_admin_email_is_reported(
        self, email_mock_settings: Dict[str, Any]
    ) -> None:
        """Test that a missing ADMIN_EMAIL reports E021 when required."""
        settings_manager.load({"EMAIL": email_mock_settings})
        errors = check_email_settings(require_admin_email=True)

        assert len(errors) == 1
        assert errors[0].id == "fast_logging.E021"
        assert "ADMIN_EMAIL" in errors[0].msg

    def test_empty_email_block_reports_every_missing_setting(self) -> None:
        """Test that an empty EMAIL block lists all required settings as missing."""
        settings_manager.load({"EMAIL": {}})
        errors = check_email_settings()

        assert len(errors) == 1
        for setting in (
            "EMAIL_HOST",
            "EMAIL_PORT",
            "EMAIL_HOST_USER",
            "EMAIL_HOST_PASSWORD",
            "EMAIL_USE_TLS",
            "DEFAULT_FROM_EMAIL",
            "ADMIN_EMAIL",
        ):
            assert setting in errors[0].msg

    def test_falsy_value_counts_as_missing(
        self, admin_email_mock_settings: Dict[str, Any]
    ) -> None:
        """Test that an empty-string setting is treated as missing."""
        settings = {**admin_email_mock_settings, "EMAIL_HOST": ""}
        settings_manager.load({"EMAIL": settings})
        errors = check_email_settings()

        assert len(errors) == 1
        assert "EMAIL_HOST" in errors[0].msg

    def test_repeated_calls_do_not_accumulate_settings(
        self, email_mock_settings: Dict[str, Any]
    ) -> None:
        """Test that the required-settings list is rebuilt on every call."""
        settings_manager.load({"EMAIL": email_mock_settings})

        first = check_email_settings()
        second = check_email_settings()

        assert first[0].msg == second[0].msg
        assert second[0].msg.count("ADMIN_EMAIL") == 1

    def test_error_carries_a_hint(self) -> None:
        """Test that the reported error includes a remediation hint."""
        settings_manager.load({"EMAIL": {}})
        errors = check_email_settings()

        assert errors[0].hint
        assert "EMAIL block" in errors[0].hint

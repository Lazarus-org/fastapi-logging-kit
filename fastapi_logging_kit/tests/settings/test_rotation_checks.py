import sys
from typing import List

import pytest

from fastapi_logging_kit.checks import Error
from fastapi_logging_kit.settings import settings_manager
from fastapi_logging_kit.settings.checks import check_rotation_settings
from fastapi_logging_kit.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON

pytestmark = [
    pytest.mark.settings,
    pytest.mark.settings_rotation_checks,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


def error_ids(errors: List[Error]) -> List[str]:
    """Return the ids of the supplied errors."""
    return [error.id for error in errors if error.id]


class TestValidRotationSettings:
    """Test suite for `check_rotation_settings` with valid configuration."""

    def test_defaults_report_no_errors(self) -> None:
        """Test that the packaged rotation defaults pass validation."""
        settings_manager.reset()
        assert check_rotation_settings({}) == []

    def test_valid_size_rotation(self) -> None:
        """Test that a well-formed size rotation config passes validation."""
        settings_manager.load(
            {
                "LOG_ROTATION": {
                    "TYPE": "size",
                    "MAX_BYTES": 2048,
                    "BACKUP_COUNT": 3,
                    "COMPRESS": True,
                }
            }
        )
        assert check_rotation_settings({}) == []

    def test_valid_time_rotation_with_overrides(self) -> None:
        """Test that valid per-level overrides pass validation."""
        settings_manager.load(
            {
                "LOG_ROTATION": {"TYPE": "time", "WHEN": "midnight", "INTERVAL": 1},
                "LOG_ROTATION_OVERRIDES": {
                    "ERROR": {"TYPE": "size", "MAX_BYTES": 1024},
                    "CRITICAL": {"TYPE": "none"},
                },
            }
        )
        assert check_rotation_settings({}) == []


class TestInvalidRotationSettings:
    """Test suite for the failure branches of `check_rotation_settings`."""

    def test_invalid_rotation_type(self) -> None:
        """Test that an unknown rotation TYPE reports E031."""
        settings_manager.load({"LOG_ROTATION": {"TYPE": "hourly"}})
        assert "fastapi_logging_kit.E031_LOG_ROTATION" in error_ids(
            check_rotation_settings({})
        )

    def test_invalid_max_bytes(self) -> None:
        """Test that a non-positive MAX_BYTES reports E032."""
        settings_manager.load({"LOG_ROTATION": {"TYPE": "size", "MAX_BYTES": 0}})
        assert "fastapi_logging_kit.E032_LOG_ROTATION" in error_ids(
            check_rotation_settings({})
        )

    def test_invalid_backup_count(self) -> None:
        """Test that a negative BACKUP_COUNT reports E033."""
        settings_manager.load({"LOG_ROTATION": {"BACKUP_COUNT": -1}})
        assert "fastapi_logging_kit.E033_LOG_ROTATION" in error_ids(
            check_rotation_settings({})
        )

    def test_invalid_when(self) -> None:
        """Test that an unknown WHEN value reports E034."""
        settings_manager.load({"LOG_ROTATION": {"TYPE": "time", "WHEN": "fortnight"}})
        assert "fastapi_logging_kit.E034_LOG_ROTATION" in error_ids(
            check_rotation_settings({})
        )

    def test_invalid_interval(self) -> None:
        """Test that a zero INTERVAL reports E035."""
        settings_manager.load({"LOG_ROTATION": {"TYPE": "time", "INTERVAL": 0}})
        assert "fastapi_logging_kit.E035_LOG_ROTATION" in error_ids(
            check_rotation_settings({})
        )

    def test_invalid_compress(self) -> None:
        """Test that a non-boolean COMPRESS reports E036."""
        settings_manager.load({"LOG_ROTATION": {"COMPRESS": "yes"}})
        assert "fastapi_logging_kit.E036_LOG_ROTATION" in error_ids(
            check_rotation_settings({})
        )

    def test_overrides_not_a_dictionary(self) -> None:
        """Test that a non-dict LOG_ROTATION_OVERRIDES reports E037."""
        settings_manager.load({"LOG_ROTATION_OVERRIDES": ["ERROR"]})
        assert "fastapi_logging_kit.E037_LOG_ROTATION_OVERRIDES" in error_ids(
            check_rotation_settings({})
        )

    def test_override_with_invalid_level(self) -> None:
        """Test that an unknown level in the overrides reports E038."""
        settings_manager.load({"LOG_ROTATION_OVERRIDES": {"TRACE": {"TYPE": "size"}}})
        assert "fastapi_logging_kit.E038_LOG_ROTATION_OVERRIDES" in error_ids(
            check_rotation_settings({})
        )

    def test_override_with_invalid_sub_config(self) -> None:
        """Test that a bad sub-config under a valid level is reported per-level."""
        settings_manager.load(
            {"LOG_ROTATION_OVERRIDES": {"ERROR": {"TYPE": "weekly"}}}
        )
        assert "fastapi_logging_kit.E031_LOG_ROTATION_OVERRIDES['ERROR']" in error_ids(
            check_rotation_settings({})
        )

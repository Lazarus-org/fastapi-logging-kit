import sys
from typing import List

import pytest

from fastapi_logging_kit.checks import Error
from fastapi_logging_kit.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON
from fastapi_logging_kit.validators.config_validators import (
    validate_rotation_config,
    validate_rotation_overrides,
)

pytestmark = [
    pytest.mark.validators,
    pytest.mark.validators_rotation,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]

VALID_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def error_ids(errors: List[Error]) -> List[str]:
    """Return the ids of the supplied errors."""
    return [error.id for error in errors if error.id]


class TestValidateRotationConfig:
    """Test suite for `validate_rotation_config`."""

    def test_empty_config_is_valid(self) -> None:
        """Test that an empty config defaults to TYPE 'none' and passes."""
        assert validate_rotation_config({}, "ROTATION", VALID_LEVELS) == []

    def test_full_valid_config(self) -> None:
        """Test that a fully populated valid config produces no errors."""
        config = {
            "TYPE": "time",
            "MAX_BYTES": 1024,
            "BACKUP_COUNT": 0,
            "WHEN": "midnight",
            "INTERVAL": 1,
            "COMPRESS": True,
        }
        assert validate_rotation_config(config, "ROTATION", VALID_LEVELS) == []

    def test_type_is_case_insensitive(self) -> None:
        """Test that an uppercase TYPE value is accepted."""
        assert validate_rotation_config({"TYPE": "SIZE"}, "ROTATION", VALID_LEVELS) == []

    def test_not_a_dictionary(self) -> None:
        """Test that a non-dict config reports E030 and stops."""
        errors = validate_rotation_config("size", "ROTATION", VALID_LEVELS)  # type: ignore[arg-type]

        assert len(errors) == 1
        assert errors[0].id == "fastapi_logging_kit.E030_ROTATION"

    def test_invalid_type(self) -> None:
        """Test that an unknown TYPE reports E031."""
        errors = validate_rotation_config({"TYPE": "daily"}, "ROTATION", VALID_LEVELS)

        assert error_ids(errors) == ["fastapi_logging_kit.E031_ROTATION"]

    def test_invalid_max_bytes_value(self) -> None:
        """Test that a non-positive MAX_BYTES reports E032."""
        errors = validate_rotation_config({"MAX_BYTES": 0}, "ROTATION", VALID_LEVELS)

        assert error_ids(errors) == ["fastapi_logging_kit.E032_ROTATION"]

    def test_invalid_max_bytes_type(self) -> None:
        """Test that a non-integer MAX_BYTES reports E032."""
        errors = validate_rotation_config(
            {"MAX_BYTES": "10MB"}, "ROTATION", VALID_LEVELS
        )

        assert error_ids(errors) == ["fastapi_logging_kit.E032_ROTATION"]

    def test_invalid_backup_count_value(self) -> None:
        """Test that a negative BACKUP_COUNT reports E033."""
        errors = validate_rotation_config(
            {"BACKUP_COUNT": -1}, "ROTATION", VALID_LEVELS
        )

        assert error_ids(errors) == ["fastapi_logging_kit.E033_ROTATION"]

    def test_invalid_backup_count_type(self) -> None:
        """Test that a non-integer BACKUP_COUNT reports E033."""
        errors = validate_rotation_config(
            {"BACKUP_COUNT": "five"}, "ROTATION", VALID_LEVELS
        )

        assert error_ids(errors) == ["fastapi_logging_kit.E033_ROTATION"]

    def test_invalid_when(self) -> None:
        """Test that an unknown WHEN reports E034."""
        errors = validate_rotation_config({"WHEN": "yearly"}, "ROTATION", VALID_LEVELS)

        assert error_ids(errors) == ["fastapi_logging_kit.E034_ROTATION"]

    def test_when_is_case_insensitive(self) -> None:
        """Test that an uppercase WHEN value is accepted."""
        assert validate_rotation_config({"WHEN": "W0"}, "ROTATION", VALID_LEVELS) == []

    def test_invalid_interval_value(self) -> None:
        """Test that a zero INTERVAL reports E035."""
        errors = validate_rotation_config({"INTERVAL": 0}, "ROTATION", VALID_LEVELS)

        assert error_ids(errors) == ["fastapi_logging_kit.E035_ROTATION"]

    def test_invalid_interval_type(self) -> None:
        """Test that a non-integer INTERVAL reports E035."""
        errors = validate_rotation_config({"INTERVAL": "1"}, "ROTATION", VALID_LEVELS)

        assert error_ids(errors) == ["fastapi_logging_kit.E035_ROTATION"]

    def test_invalid_compress(self) -> None:
        """Test that a non-boolean COMPRESS reports E036."""
        errors = validate_rotation_config({"COMPRESS": "yes"}, "ROTATION", VALID_LEVELS)

        assert error_ids(errors) == ["fastapi_logging_kit.E036_ROTATION"]

    def test_multiple_problems_are_all_reported(self) -> None:
        """Test that every invalid key contributes its own error."""
        config = {
            "TYPE": "daily",
            "MAX_BYTES": -1,
            "BACKUP_COUNT": -1,
            "WHEN": "never",
            "INTERVAL": 0,
            "COMPRESS": 1,
        }
        errors = validate_rotation_config(config, "ROTATION", VALID_LEVELS)

        assert error_ids(errors) == [
            "fastapi_logging_kit.E031_ROTATION",
            "fastapi_logging_kit.E032_ROTATION",
            "fastapi_logging_kit.E033_ROTATION",
            "fastapi_logging_kit.E034_ROTATION",
            "fastapi_logging_kit.E035_ROTATION",
            "fastapi_logging_kit.E036_ROTATION",
        ]


class TestValidateRotationOverrides:
    """Test suite for `validate_rotation_overrides`."""

    def test_empty_overrides_are_valid(self) -> None:
        """Test that an empty overrides mapping produces no errors."""
        assert validate_rotation_overrides({}, "OVERRIDES", VALID_LEVELS) == []

    def test_valid_overrides(self) -> None:
        """Test that valid per-level sub-configs produce no errors."""
        overrides = {
            "ERROR": {"TYPE": "size", "MAX_BYTES": 1024},
            "DEBUG": {"TYPE": "none"},
        }
        assert validate_rotation_overrides(overrides, "OVERRIDES", VALID_LEVELS) == []

    def test_not_a_dictionary(self) -> None:
        """Test that non-dict overrides report E037 and stop."""
        errors = validate_rotation_overrides(["ERROR"], "OVERRIDES", VALID_LEVELS)  # type: ignore[arg-type]

        assert len(errors) == 1
        assert errors[0].id == "fastapi_logging_kit.E037_OVERRIDES"

    def test_invalid_level_key(self) -> None:
        """Test that an unknown log level reports E038."""
        errors = validate_rotation_overrides(
            {"TRACE": {"TYPE": "size"}}, "OVERRIDES", VALID_LEVELS
        )

        assert error_ids(errors) == ["fastapi_logging_kit.E038_OVERRIDES"]

    def test_valid_level_with_invalid_sub_config(self) -> None:
        """Test that a bad sub-config is reported with the per-level config name."""
        errors = validate_rotation_overrides(
            {"ERROR": {"TYPE": "daily"}}, "OVERRIDES", VALID_LEVELS
        )

        assert error_ids(errors) == ["fastapi_logging_kit.E031_OVERRIDES['ERROR']"]

    def test_valid_level_with_non_dict_sub_config(self) -> None:
        """Test that a non-dict sub-config reports E030 for that level."""
        errors = validate_rotation_overrides(
            {"ERROR": "size"}, "OVERRIDES", VALID_LEVELS
        )

        assert error_ids(errors) == ["fastapi_logging_kit.E030_OVERRIDES['ERROR']"]

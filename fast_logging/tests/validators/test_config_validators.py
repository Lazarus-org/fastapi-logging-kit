import os
import sys
from pathlib import Path

import pytest

from fast_logging.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON
from fast_logging.validators.config_validators import (
    validate_boolean_setting,
    validate_date_format,
    validate_directory,
    validate_email_notifier,
    validate_extra_log_files,
    validate_format_option,
    validate_format_string,
    validate_integer_setting,
    validate_log_file_format_types,
    validate_log_levels,
)

pytestmark = [
    pytest.mark.validators,
    pytest.mark.config_validator,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]

VALID_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class TestValidateDirectory:
    """Test suite for `validate_directory`."""

    def test_existing_directory_is_valid(self, temp_log_directory: str) -> None:
        """Test that an existing directory produces no errors."""
        assert validate_directory(temp_log_directory, "LOG_DIR") == []

    def test_non_string_path(self) -> None:
        """Test that a non-string path reports E001."""
        errors = validate_directory(123, "LOG_DIR")  # type: ignore[arg-type]

        assert len(errors) == 1
        assert errors[0].id == "fast_logging.E001_LOG_DIR"

    def test_missing_path_is_created(self, tmp_path: Path) -> None:
        """Test that a missing path whose parent can be created is accepted."""
        target = os.path.join(str(tmp_path), "nested", "logs")
        assert validate_directory(target, "LOG_DIR") == []
        assert os.path.isdir(os.path.dirname(target))

    def test_uncreatable_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that a path which cannot be created reports E002."""

        def boom(*args: object, **kwargs: object) -> None:
            raise OSError("permission denied")

        monkeypatch.setattr(os, "makedirs", boom)
        errors = validate_directory(os.path.join(str(tmp_path), "x", "y"), "LOG_DIR")

        assert len(errors) == 1
        assert errors[0].id == "fast_logging.E002_LOG_DIR"

    def test_path_is_a_file_not_a_directory(self, tmp_path: Path) -> None:
        """Test that an existing file path reports E003."""
        file_path = tmp_path / "not_a_dir.txt"
        file_path.write_text("content", encoding="utf-8")

        errors = validate_directory(str(file_path), "LOG_DIR")

        assert len(errors) == 1
        assert errors[0].id == "fast_logging.E003_LOG_DIR"


class TestValidateLogLevels:
    """Test suite for `validate_log_levels`."""

    def test_valid_levels(self) -> None:
        """Test that a list of known levels produces no errors."""
        assert validate_log_levels(["DEBUG", "ERROR"], "LEVELS", VALID_LEVELS) == []

    def test_not_a_list(self) -> None:
        """Test that a non-list value reports E004."""
        errors = validate_log_levels("DEBUG", "LEVELS", VALID_LEVELS)  # type: ignore[arg-type]

        assert errors[0].id == "fast_logging.E004_LEVELS"

    def test_empty_list(self) -> None:
        """Test that an empty list reports E005."""
        errors = validate_log_levels([], "LEVELS", VALID_LEVELS)

        assert errors[0].id == "fast_logging.E005_LEVELS"

    def test_non_string_element(self) -> None:
        """Test that a non-string element reports E006."""
        errors = validate_log_levels([123], "LEVELS", VALID_LEVELS)  # type: ignore[list-item]

        assert errors[0].id == "fast_logging.E006_LEVELS"

    def test_unknown_level(self) -> None:
        """Test that an unrecognized level reports E007."""
        errors = validate_log_levels(["TRACE"], "LEVELS", VALID_LEVELS)  # type: ignore[list-item]

        assert errors[0].id == "fast_logging.E007_LEVELS"


class TestValidateFormatString:
    """Test suite for `validate_format_string`."""

    def test_valid_format_string(self) -> None:
        """Test that a string with known specifiers produces no errors."""
        assert validate_format_string("%(levelname)s %(message)s", "FMT") == []

    def test_not_a_string(self) -> None:
        """Test that a non-string value reports E008."""
        errors = validate_format_string(42, "FMT")  # type: ignore[arg-type]

        assert errors[0].id == "fast_logging.E008_FMT"

    def test_empty_string(self) -> None:
        """Test that an empty string reports E009."""
        errors = validate_format_string("", "FMT")

        assert errors[0].id == "fast_logging.E009_FMT"

    def test_no_format_specifiers(self) -> None:
        """Test that a string without specifiers reports E010."""
        errors = validate_format_string("plain text", "FMT")

        assert errors[0].id == "fast_logging.E010_FMT"

    def test_invalid_format_specifiers(self) -> None:
        """Test that unknown specifiers report E011."""
        errors = validate_format_string("%(nope)s %(message)s", "FMT")

        assert errors[0].id == "fast_logging.E011_FMT"


class TestValidateFormatOption:
    """Test suite for `validate_format_option`."""

    def test_valid_integer_option(self) -> None:
        """Test that a known format option number produces no errors."""
        assert validate_format_option(1, "FMT") == []

    def test_invalid_integer_option(self) -> None:
        """Test that an out-of-range format option reports E012."""
        errors = validate_format_option(999, "FMT")

        assert errors[0].id == "fast_logging.E012_FMT"

    def test_string_option_is_validated_as_a_format_string(self) -> None:
        """Test that a string option is delegated to the format-string validator."""
        errors = validate_format_option("plain text", "FMT")

        assert errors[0].id == "fast_logging.E010_FMT"

    def test_invalid_type(self) -> None:
        """Test that a value of an unsupported type reports E013."""
        errors = validate_format_option([1], "FMT")  # type: ignore[arg-type]

        assert errors[0].id == "fast_logging.E013_FMT"


class TestValidateBooleanSetting:
    """Test suite for `validate_boolean_setting`."""

    def test_valid_boolean(self) -> None:
        """Test that a boolean value produces no errors."""
        assert validate_boolean_setting(True, "FLAG") == []
        assert validate_boolean_setting(False, "FLAG") == []

    def test_non_boolean(self) -> None:
        """Test that a non-boolean value reports E014."""
        errors = validate_boolean_setting("true", "FLAG")  # type: ignore[arg-type]

        assert errors[0].id == "fast_logging.E014_FLAG"


class TestValidateDateFormat:
    """Test suite for `validate_date_format`."""

    def test_valid_date_format(self) -> None:
        """Test that a valid strftime string produces no errors."""
        assert validate_date_format("%Y-%m-%d %H:%M:%S", "DATE_FMT") == []

    def test_not_a_string(self) -> None:
        """Test that a non-string date format reports E015."""
        errors = validate_date_format(123, "DATE_FMT")  # type: ignore[arg-type]

        assert errors[0].id == "fast_logging.E015_DATE_FMT"

    def test_invalid_directives(self) -> None:
        """Test that unknown strftime directives report E016."""
        errors = validate_date_format("%Q-%K", "DATE_FMT")

        assert errors[0].id == "fast_logging.E016_DATE_FMT"


class TestValidateEmailNotifier:
    """Test suite for `validate_email_notifier`."""

    def test_valid_notifier_config(self) -> None:
        """Test that a well-formed notifier config produces no errors."""
        config = {
            "ENABLE": True,
            "NOTIFY_ERROR": False,
            "NOTIFY_CRITICAL": True,
            "USE_TEMPLATE": False,
            "LOG_FORMAT": 1,
        }
        assert validate_email_notifier(config) == []  # type: ignore[arg-type]

    def test_not_a_dictionary(self) -> None:
        """Test that a non-dict notifier config reports E017."""
        errors = validate_email_notifier("enabled")  # type: ignore[arg-type]

        assert len(errors) == 1
        assert errors[0].id == "fast_logging.E017_LOG_EMAIL_NOTIFIER"

    def test_string_log_format_is_validated(self) -> None:
        """Test that a string LOG_FORMAT is validated as a format string."""
        errors = validate_email_notifier({"LOG_FORMAT": "plain"})  # type: ignore[arg-type]

        assert errors[0].id == "fast_logging.E010_LOG_EMAIL_NOTIFIER['LOG_FORMAT']"

    def test_unknown_key_type(self) -> None:
        """Test that a value of an unexpected type reports E018."""
        errors = validate_email_notifier({"ENABLE": ["yes"]})  # type: ignore[arg-type]

        assert errors[0].id == "fast_logging.E018_LOG_EMAIL_NOTIFIER['ENABLE']"

    def test_boolean_under_unknown_key(self) -> None:
        """Test that a boolean under an unrecognized key reports E018."""
        errors = validate_email_notifier({"SOMETHING_ELSE": True})  # type: ignore[arg-type]

        assert errors[0].id == "fast_logging.E018_LOG_EMAIL_NOTIFIER['SOMETHING_ELSE']"


class TestValidateIntegerSetting:
    """Test suite for `validate_integer_setting`."""

    def test_valid_integer(self) -> None:
        """Test that a non-negative integer produces no errors."""
        assert validate_integer_setting(0, "SIZE") == []
        assert validate_integer_setting(100, "SIZE") == []

    def test_negative_integer(self) -> None:
        """Test that a negative integer reports E019."""
        errors = validate_integer_setting(-5, "SIZE")

        assert errors[0].id == "fast_logging.E019_SIZE"

    def test_non_integer(self) -> None:
        """Test that a non-integer value reports E019."""
        errors = validate_integer_setting("100", "SIZE")  # type: ignore[arg-type]

        assert errors[0].id == "fast_logging.E019_SIZE"


class TestValidateLogFileFormatTypes:
    """Test suite for `validate_log_file_format_types`."""

    def test_valid_format_types(self) -> None:
        """Test that recognized format types produce no errors."""
        errors = validate_log_file_format_types(
            {"DEBUG": "JSON", "INFO": "normal"},
            "TYPES",
            VALID_LEVELS,
            ["JSON", "XML", "FLAT", "NORMAL"],
        )
        assert errors == []

    def test_not_a_dictionary(self) -> None:
        """Test that a non-dict value reports E022."""
        errors = validate_log_file_format_types(
            ["JSON"], "TYPES", VALID_LEVELS, ["JSON"]  # type: ignore[arg-type]
        )

        assert errors[0].id == "fast_logging.E022_TYPES"

    def test_invalid_level(self) -> None:
        """Test that an unknown log level key reports E023."""
        errors = validate_log_file_format_types(
            {"TRACE": "JSON"}, "TYPES", VALID_LEVELS, ["JSON"]
        )

        assert errors[0].id == "fast_logging.E023_TYPES"

    def test_invalid_format_type(self) -> None:
        """Test that an unsupported format type reports E024."""
        errors = validate_log_file_format_types(
            {"DEBUG": "YAML"}, "TYPES", VALID_LEVELS, ["JSON"]
        )

        assert errors[0].id == "fast_logging.E024_TYPES"


class TestValidateExtraLogFiles:
    """Test suite for `validate_extra_log_files`."""

    def test_valid_extra_log_files(self) -> None:
        """Test that boolean values under known levels produce no errors."""
        assert validate_extra_log_files({"DEBUG": True}, "EXTRA", VALID_LEVELS) == []

    def test_not_a_dictionary(self) -> None:
        """Test that a non-dict value reports E025."""
        errors = validate_extra_log_files(True, "EXTRA", VALID_LEVELS)  # type: ignore[arg-type]

        assert errors[0].id == "fast_logging.E025_EXTRA"

    def test_invalid_level(self) -> None:
        """Test that an unknown log level key reports E026."""
        errors = validate_extra_log_files({"TRACE": True}, "EXTRA", VALID_LEVELS)

        assert errors[0].id == "fast_logging.E026_EXTRA"

    def test_non_boolean_value(self) -> None:
        """Test that a non-boolean value reports E027."""
        errors = validate_extra_log_files({"DEBUG": "yes"}, "EXTRA", VALID_LEVELS)

        assert errors[0].id == "fast_logging.E027_EXTRA"

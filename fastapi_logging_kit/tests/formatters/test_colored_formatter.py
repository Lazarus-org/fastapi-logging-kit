import logging
import sys

import pytest

from fastapi_logging_kit.constants.ansi_colors import LOG_LEVEL_COLORS, AnsiColors
from fastapi_logging_kit.formatters import ColoredFormatter
from fastapi_logging_kit.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON

pytestmark = [
    pytest.mark.formatters,
    pytest.mark.colored_formatter,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


class TestColoredFormatterFormat:
    """Test suite for `ColoredFormatter.format`."""

    def test_colorizes_plain_format_string(
        self, colored_formatter: ColoredFormatter, info_log_record: logging.LogRecord
    ) -> None:
        """Test that a format string without ANSI codes gets colorized."""
        output = colored_formatter.format(info_log_record)
        assert LOG_LEVEL_COLORS["INFO"] in output
        assert AnsiColors.RESET in output
        assert "This is an info message" in output

    def test_leaves_preformatted_ansi_format_untouched(
        self, info_log_record: logging.LogRecord
    ) -> None:
        """Test that a format string already containing ANSI codes is not recolorized."""
        fmt = f"{AnsiColors.GREEN}%(levelname)s{AnsiColors.RESET} | %(message)s"
        formatter = ColoredFormatter(fmt=fmt)
        output = formatter.format(info_log_record)
        assert output == f"{AnsiColors.GREEN}INFO{AnsiColors.RESET} | This is an info message"
        assert AnsiColors.ITALIC not in output

    def test_restores_original_format_after_formatting(
        self, colored_formatter: ColoredFormatter, error_log_record: logging.LogRecord
    ) -> None:
        """Test that `self._style._fmt` is restored once formatting completes."""
        original = colored_formatter._style._fmt
        colored_formatter.format(error_log_record)
        assert colored_formatter._style._fmt == original

    def test_uses_level_specific_color(
        self, colored_formatter: ColoredFormatter, error_log_record: logging.LogRecord
    ) -> None:
        """Test that the colour applied to the level name matches the record level."""
        output = colored_formatter.format(error_log_record)
        assert LOG_LEVEL_COLORS["ERROR"] in output

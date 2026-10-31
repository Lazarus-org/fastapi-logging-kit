import sys

import pytest

from fastapi_logging_kit.constants.ansi_colors import LOG_LEVEL_COLORS, AnsiColors
from fastapi_logging_kit.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON
from fastapi_logging_kit.utils.console_colorizer import colorize_log_format

pytestmark = [
    pytest.mark.utils,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]

PLACEHOLDERS = [
    ("%(asctime)s", AnsiColors.BRIGHT_BLUE),
    ("%(created)f", AnsiColors.BRIGHT_BLUE),
    ("%(relativeCreated)d", AnsiColors.MAGENTA),
    ("%(msecs)d", AnsiColors.YELLOW),
    ("%(levelno)d", AnsiColors.RED),
    ("%(exc_info)s", AnsiColors.RED),
    ("%(exc_text)s", AnsiColors.RED),
    ("%(name)s", AnsiColors.BRIGHT_MAGENTA),
    ("%(module)s", AnsiColors.PINK),
    ("%(stack_info)s", AnsiColors.YELLOW),
    ("%(filename)s", AnsiColors.YELLOW),
    ("%(pathname)s", AnsiColors.CYAN),
    ("%(lineno)d", AnsiColors.LIGHT_PURPLE),
    ("%(funcName)s", AnsiColors.BRIGHT_BLUE),
    ("%(process)d", AnsiColors.MAGENTA),
    ("%(processName)s", AnsiColors.MAGENTA),
    ("%(thread)d", AnsiColors.CYAN),
    ("%(threadName)s", AnsiColors.BRIGHT_MAGENTA),
    ("%(message)s", AnsiColors.ITALIC),
    ("%(context)s", AnsiColors.MAGENTA),
]


class TestColorizeLogFormat:
    """Test suite for the `colorize_log_format` function."""

    @pytest.mark.parametrize("placeholder, color", PLACEHOLDERS)
    def test_wraps_known_placeholder_in_its_color(
        self, placeholder: str, color: str
    ) -> None:
        """Test that each known placeholder is wrapped in its designated colour."""
        assert (
            colorize_log_format(placeholder, "INFO")
            == f"{color}{placeholder}{AnsiColors.RESET}"
        )

    def test_colorizes_levelname_using_level_color(self) -> None:
        """Test that `%(levelname)s` is coloured according to the level name."""
        assert (
            colorize_log_format("%(levelname)s", "ERROR")
            == f"{LOG_LEVEL_COLORS['ERROR']}%(levelname)s{AnsiColors.RESET}"
        )

    def test_unknown_levelname_yields_no_color_prefix(self) -> None:
        """Test that an unknown level name results in an empty colour prefix."""
        assert (
            colorize_log_format("%(levelname)s", "NOTALEVEL")
            == f"%(levelname)s{AnsiColors.RESET}"
        )

    def test_colorizes_multiple_placeholders_in_one_format(self) -> None:
        """Test that every placeholder in a composite format string is colorized."""
        result = colorize_log_format("%(levelname)s | %(asctime)s | %(message)s", "INFO")
        assert LOG_LEVEL_COLORS["INFO"] in result
        assert AnsiColors.BRIGHT_BLUE in result
        assert AnsiColors.ITALIC in result

    def test_leaves_unknown_text_unchanged(self) -> None:
        """Test that text containing no known placeholders is returned as-is."""
        assert colorize_log_format("just some text", "INFO") == "just some text"

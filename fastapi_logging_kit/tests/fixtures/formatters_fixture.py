import pytest

from fastapi_logging_kit.formatters import (
    ColoredFormatter,
    FLATFormatter,
    JSONFormatter,
    XMLFormatter,
)

FORMAT_STRING = "%(levelname)s | %(asctime)s | %(message)s"


@pytest.fixture
def json_formatter() -> JSONFormatter:
    """Return a JSONFormatter using the shared format string.

    Returns:
        JSONFormatter: The formatter.

    """
    return JSONFormatter(fmt=FORMAT_STRING)


@pytest.fixture
def xml_formatter() -> XMLFormatter:
    """Return an XMLFormatter using the shared format string.

    Returns:
        XMLFormatter: The formatter.

    """
    return XMLFormatter(fmt=FORMAT_STRING)


@pytest.fixture
def flat_formatter() -> FLATFormatter:
    """Return a FLATFormatter using the shared format string.

    Returns:
        FLATFormatter: The formatter.

    """
    return FLATFormatter(fmt=FORMAT_STRING)


@pytest.fixture
def colored_formatter() -> ColoredFormatter:
    """Return a ColoredFormatter using the shared format string.

    Returns:
        ColoredFormatter: The formatter.

    """
    return ColoredFormatter(fmt=FORMAT_STRING)

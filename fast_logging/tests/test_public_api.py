import sys

import pytest

import fast_logging
from fast_logging.exceptions import FastLoggingError, ImproperlyConfigured
from fast_logging.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


class TestExceptions:
    """Test suite for the exception hierarchy of `fast_logging`."""

    def test_improperly_configured_subclasses_the_base_error(self) -> None:
        """Test that ImproperlyConfigured derives from FastLoggingError."""
        assert issubclass(ImproperlyConfigured, FastLoggingError)
        assert issubclass(FastLoggingError, Exception)

    def test_improperly_configured_is_catchable_as_the_base_error(self) -> None:
        """Test that the base class catches the configuration error."""
        with pytest.raises(FastLoggingError, match="missing SMTP settings"):
            raise ImproperlyConfigured("missing SMTP settings")


class TestPublicApi:
    """Test suite for the names exported by the `fast_logging` package."""

    @pytest.mark.parametrize("name", fast_logging.__all__)
    def test_every_exported_name_is_importable(self, name: str) -> None:
        """Test that each name in ``__all__`` exists on the package.

        Args:
            name (str): The exported name under test.

        """
        assert hasattr(fast_logging, name)

    def test_all_is_sorted_and_unique(self) -> None:
        """Test that ``__all__`` holds unique, sorted names."""
        assert fast_logging.__all__ == sorted(set(fast_logging.__all__))

    def test_version_is_a_string(self) -> None:
        """Test that the package exposes a non-empty version string."""
        assert isinstance(fast_logging.__version__, str)
        assert fast_logging.__version__

    def test_setup_logging_is_the_documented_entry_point(self) -> None:
        """Test that ``setup_logging`` is re-exported from the app module."""
        from fast_logging.app import setup_logging

        assert fast_logging.setup_logging is setup_logging

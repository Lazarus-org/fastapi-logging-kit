import logging
import sys
from pathlib import Path
from typing import Any, Iterator

import pytest

from fast_logging.settings import settings_manager
from fast_logging.settings.conf import LogManager
from fast_logging.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON
from fast_logging.utils.context_manager import config_setup

pytestmark = [
    pytest.mark.utils,
    pytest.mark.utils_context_manager,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


@pytest.fixture(autouse=True)
def quiet_log_manager(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stop ``LogManager.set_conf`` from reconfiguring process-wide logging.

    Args:
        monkeypatch (pytest.MonkeyPatch): The patching helper.

    """
    monkeypatch.setattr(LogManager, "set_conf", lambda self: None)


@pytest.fixture
def manual_configuration(tmp_path: Path) -> Iterator[None]:
    """Configure the package with auto initialization turned off.

    Args:
        tmp_path (Path): The temporary log directory root.

    Yields:
        None

    """
    settings_manager.load(
        {
            "AUTO_INITIALIZATION_ENABLE": False,
            "LOG_DIR": str(tmp_path / "logs"),
            "LOG_FILE_LEVELS": ["INFO"],
        }
    )
    yield


class TestConfigSetupGuard:
    """Test suite for the auto initialization guard of `config_setup`."""

    def test_raises_when_auto_initialization_is_enabled(self) -> None:
        """Test that the context manager refuses to run on the default config."""
        with pytest.raises(ValueError, match="AUTO_INITIALIZATION_ENABLE"):
            with config_setup():
                pass  # pragma: no cover


class TestConfigSetup:
    """Test suite for the `config_setup` context manager."""

    def test_yields_a_log_manager(self, manual_configuration: None) -> None:
        """Test that a configured log manager is yielded.

        Args:
            manual_configuration (None): The manual configuration fixture.

        """
        with config_setup() as log_manager:
            assert isinstance(log_manager, LogManager)
            assert log_manager.get_log_file("INFO") is not None

    def test_restores_the_root_logger(self, manual_configuration: None) -> None:
        """Test that the root logger is restored once the block ends.

        Args:
            manual_configuration (None): The manual configuration fixture.

        """
        root = logging.getLogger()
        original_level = root.level
        original_handlers = root.handlers.copy()
        original_loggers = set(root.manager.loggerDict)

        with config_setup():
            root.setLevel(logging.CRITICAL)
            root.addHandler(logging.NullHandler())
            logging.getLogger("fast_logging.tests.temporary_logger")

        assert root.level == original_level
        assert root.handlers == original_handlers
        assert set(root.manager.loggerDict) == original_loggers

    def test_restores_the_root_logger_when_the_body_raises(
        self, manual_configuration: None
    ) -> None:
        """Test that restoration also happens when the block raises.

        Args:
            manual_configuration (None): The manual configuration fixture.

        """
        root = logging.getLogger()
        original_level = root.level
        original_handlers = root.handlers.copy()

        with pytest.raises(RuntimeError, match="boom"):
            with config_setup():
                root.setLevel(logging.CRITICAL)
                root.addHandler(logging.NullHandler())
                raise RuntimeError("boom")

        assert root.level == original_level
        assert root.handlers == original_handlers

    def test_restores_the_root_logger_when_setup_fails(
        self, manual_configuration: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that a failure while configuring still restores the logger.

        Args:
            manual_configuration (None): The manual configuration fixture.
            monkeypatch (pytest.MonkeyPatch): The patching helper.

        """
        root = logging.getLogger()
        original_level = root.level

        def explode(self: Any) -> None:
            raise ValueError("bad configuration")

        monkeypatch.setattr(LogManager, "create_log_files", explode)

        with pytest.raises(ValueError, match="bad configuration"):
            with config_setup():
                pass  # pragma: no cover

        assert root.level == original_level

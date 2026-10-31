import logging
import logging.handlers
import os
import sys
from typing import Any, Iterator

import pytest

from fastapi_logging_kit.commands.rotate_logs import run
from fastapi_logging_kit.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON

pytestmark = [
    pytest.mark.commands,
    pytest.mark.commands_rotate_logs,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


@pytest.fixture
def isolated_loggers(monkeypatch: pytest.MonkeyPatch) -> Iterator[logging.Logger]:
    """Yield a throwaway logger that is the only one the command can see.

    The command walks every logger in the manager, so both the manager
    dictionary and the root handlers are replaced for the duration of
    the test to keep other suites from leaking in.

    Args:
        monkeypatch (pytest.MonkeyPatch): The patching helper.

    Yields:
        logging.Logger: The isolated logger.

    """
    target = logging.getLogger("fastapi_logging_kit.tests.rotate")
    target.handlers = []
    monkeypatch.setattr(logging.root, "handlers", [])
    monkeypatch.setattr(logging.Logger.manager, "loggerDict", {"target": target})

    yield target

    for handler in list(target.handlers):
        handler.close()
        target.removeHandler(handler)


class TestRotateLogsCommand:
    """Test suite for the `rotate_logs` command."""

    def test_rotates_rotating_file_handler(
        self, isolated_loggers: logging.Logger, tmp_path: Any
    ) -> None:
        """Test that a RotatingFileHandler is rolled over."""
        log_path = str(tmp_path / "app.log")
        handler = logging.handlers.RotatingFileHandler(
            log_path, maxBytes=1024, backupCount=2
        )
        isolated_loggers.addHandler(handler)
        isolated_loggers.error("something happened")

        out = run(echo=False)

        assert "Rotated 1 handler(s):" in out.getvalue()
        assert log_path in out.getvalue()
        assert os.path.exists(f"{log_path}.1")

    def test_skips_plain_file_handler(
        self, isolated_loggers: logging.Logger, tmp_path: Any
    ) -> None:
        """Test that a plain FileHandler is reported as skipped."""
        log_path = str(tmp_path / "plain.log")
        isolated_loggers.addHandler(logging.FileHandler(log_path))

        out = run(echo=False)
        output = out.getvalue()

        assert "Skipped 1 plain FileHandler(s)" in output
        assert "No rotating handlers found." in output

    def test_warns_when_no_file_handlers(
        self, isolated_loggers: logging.Logger
    ) -> None:
        """Test that the command warns when nothing can be rotated."""
        isolated_loggers.addHandler(logging.NullHandler())

        out = run(echo=False)
        output = out.getvalue()

        assert "No rotating handlers found." in output
        assert "Skipped" not in output

    def test_ignores_placeholder_entries(
        self, isolated_loggers: logging.Logger, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that non-Logger entries in the manager are skipped."""
        placeholder = logging.PlaceHolder(isolated_loggers)
        monkeypatch.setattr(
            logging.Logger.manager, "loggerDict", {"placeholder": placeholder}
        )

        out = run(echo=False)

        assert "No rotating handlers found." in out.getvalue()

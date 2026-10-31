import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict

import pytest

import fastapi_logging_kit.utils.set_conf as set_conf_module
from fastapi_logging_kit.settings import settings_manager
from fastapi_logging_kit.settings.conf import LogManager
from fastapi_logging_kit.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON
from fastapi_logging_kit.utils.get_conf import get_config
from fastapi_logging_kit.utils.set_conf import set_config

pytestmark = [
    pytest.mark.utils,
    pytest.mark.utils_set_conf,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


@pytest.fixture(autouse=True)
def quiet_log_manager(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stop ``LogManager.set_conf`` from reconfiguring process-wide logging.

    Args:
        monkeypatch (pytest.MonkeyPatch): The patching helper.

    """
    monkeypatch.setattr(LogManager, "set_conf", lambda self: None)


def _load(tmp_path: Path, **overrides: Any) -> Dict[str, Any]:
    """Load a minimal configuration rooted at *tmp_path*.

    Args:
        tmp_path (Path): The directory log files are written to.
        **overrides (Any): Extra configuration keys.

    Returns:
        Dict[str, Any]: The keyword arguments for :func:`set_config`.

    """
    config: Dict[str, Any] = {
        "LOG_DIR": str(tmp_path / "logs"),
        "LOG_FILE_LEVELS": ["INFO", "ERROR"],
        "INITIALIZATION_MESSAGE_ENABLE": False,
    }
    config.update(overrides)
    settings_manager.load(config)
    return get_config()


class TestAutoInitialization:
    """Test suite for the auto initialization guard of `set_config`."""

    def test_returns_early_when_disabled(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that nothing is configured when auto initialization is off.

        Args:
            tmp_path (Path): The temporary log directory root.
            monkeypatch (pytest.MonkeyPatch): The patching helper.

        """
        conf = _load(tmp_path, AUTO_INITIALIZATION_ENABLE=False)

        def explode(*args: Any, **kwargs: Any) -> None:
            raise AssertionError("LogManager must not be built")

        monkeypatch.setattr(set_conf_module, "LogManager", explode)

        set_config(**conf)

        assert not (tmp_path / "logs").exists()


class TestSuccessPath:
    """Test suite for the successful configuration path of `set_config`."""

    def test_creates_the_log_files(self, tmp_path: Path) -> None:
        """Test that a log file is created for every configured level.

        Args:
            tmp_path (Path): The temporary log directory root.

        """
        conf = _load(tmp_path)

        set_config(**conf)

        log_dir = tmp_path / "logs"
        assert sorted(os.listdir(log_dir)) == ["error.log", "info.log"]


class TestFailurePath:
    """Test suite for the error handling of `set_config`."""

    @pytest.mark.parametrize("exception", [ValueError, AttributeError])
    def test_warns_on_a_bad_configuration(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
        exception: type,
    ) -> None:
        """Test that a failing setup is reported as a warning.

        Args:
            tmp_path (Path): The temporary log directory root.
            monkeypatch (pytest.MonkeyPatch): The patching helper.
            caplog (pytest.LogCaptureFixture): The log capture fixture.
            exception (type): The exception raised by the log manager.

        """
        conf = _load(tmp_path, INITIALIZATION_MESSAGE_ENABLE=True)

        def explode(*args: Any, **kwargs: Any) -> None:
            raise exception("broken configuration")

        monkeypatch.setattr(set_conf_module, "LogManager", explode)

        with caplog.at_level(logging.WARNING):
            set_config(**conf)

        assert "[CONFIGURATION ERROR]" in caplog.text
        assert "Logging initialized" not in caplog.text


class TestInitializationMessage:
    """Test suite for the initialization message emitted by `set_config`."""

    def test_emitted_when_enabled(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that the summary is logged when the message is enabled.

        Args:
            tmp_path (Path): The temporary log directory root.
            caplog (pytest.LogCaptureFixture): The log capture fixture.

        """
        conf = _load(
            tmp_path,
            INITIALIZATION_MESSAGE_ENABLE=True,
            LOG_ROTATION={"TYPE": "size"},
            LOG_CONSOLE_LEVEL="",
        )

        with caplog.at_level(logging.INFO):
            set_config(**conf)

        assert "Logging initialized with the following configurations" in caplog.text
        assert "Log rotation type: size" in caplog.text
        assert "Console output level: default (DEBUG)" in caplog.text

    def test_suppressed_when_disabled(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that no summary is logged when the message is disabled.

        Args:
            tmp_path (Path): The temporary log directory root.
            caplog (pytest.LogCaptureFixture): The log capture fixture.

        """
        conf = _load(tmp_path, INITIALIZATION_MESSAGE_ENABLE=False)

        with caplog.at_level(logging.INFO):
            set_config(**conf)

        assert "Logging initialized" not in caplog.text

    def test_suppressed_by_the_run_main_env_var(
        self,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that the summary is skipped in a reloader parent process.

        Args:
            tmp_path (Path): The temporary log directory root.
            caplog (pytest.LogCaptureFixture): The log capture fixture.
            monkeypatch (pytest.MonkeyPatch): The patching helper.

        """
        conf = _load(tmp_path, INITIALIZATION_MESSAGE_ENABLE=True)
        monkeypatch.setenv("RUN_MAIN", "false")

        with caplog.at_level(logging.INFO):
            set_config(**conf)

        assert "Logging initialized" not in caplog.text

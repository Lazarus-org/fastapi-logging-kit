import gzip
import os
import sys
from pathlib import Path

import pytest

from fastapi_logging_kit.handlers.rotating_file_handler import (
    CompressedRotatingFileHandler,
    CompressedTimedRotatingFileHandler,
    _gzip_namer,
    _gzip_rotator,
)
from fastapi_logging_kit.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON

pytestmark = [
    pytest.mark.handlers,
    pytest.mark.handlers_rotating,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


class TestGzipHelpers:
    """Test suite for the module-level gzip namer and rotator."""

    def test_namer_appends_gz(self) -> None:
        """Test that the namer appends a .gz suffix to the rotated name."""
        assert _gzip_namer("app.log.1") == "app.log.1.gz"

    def test_rotator_with_plain_destination(self, tmp_path: Path) -> None:
        """Test that a destination without .gz gets the suffix added."""
        source = tmp_path / "source.log"
        source.write_text("payload", encoding="utf-8")

        _gzip_rotator(str(source), str(tmp_path / "dest.log"))

        compressed = tmp_path / "dest.log.gz"
        assert compressed.exists()
        assert not source.exists()
        with gzip.open(compressed, "rb") as handle:
            assert handle.read() == b"payload"

    def test_rotator_with_gz_destination(self, tmp_path: Path) -> None:
        """Test that a destination already ending in .gz is used as-is."""
        source = tmp_path / "source.log"
        source.write_text("payload", encoding="utf-8")

        _gzip_rotator(str(source), str(tmp_path / "dest.log.gz"))

        assert (tmp_path / "dest.log.gz").exists()
        assert not (tmp_path / "dest.log.gz.gz").exists()
        assert not source.exists()


class TestCompressedRotatingFileHandler:
    """Test suite for the size-based compressed rotating handler."""

    def test_rotator_and_namer_are_installed(self, tmp_path: Path) -> None:
        """Test that the handler wires up the gzip rotator and namer."""
        handler = CompressedRotatingFileHandler(str(tmp_path / "app.log"))
        try:
            assert handler.rotator is _gzip_rotator
            assert handler.namer is _gzip_namer
        finally:
            handler.close()

    def test_rollover_gzips_the_previous_file(self, tmp_path: Path) -> None:
        """Test that rolling over compresses the log and removes the
        original."""
        log_file = tmp_path / "app.log"
        handler = CompressedRotatingFileHandler(
            str(log_file), maxBytes=10, backupCount=2
        )
        try:
            handler.stream.write("x" * 64)
            handler.stream.flush()
            handler.doRollover()
        finally:
            handler.close()

        compressed = tmp_path / "app.log.1.gz"
        assert compressed.exists()
        assert not (tmp_path / "app.log.1").exists()
        with gzip.open(compressed, "rb") as handle:
            assert handle.read() == b"x" * 64


class TestCompressedTimedRotatingFileHandler:
    """Test suite for the time-based compressed rotating handler."""

    def test_rotator_and_namer_are_installed(self, tmp_path: Path) -> None:
        """Test that the timed handler wires up the gzip rotator and namer."""
        handler = CompressedTimedRotatingFileHandler(str(tmp_path / "timed.log"))
        try:
            assert handler.rotator is _gzip_rotator
            assert handler.namer is _gzip_namer
        finally:
            handler.close()

    def test_rollover_gzips_the_previous_file(self, tmp_path: Path) -> None:
        """Test that a timed rollover compresses the log and removes the
        original."""
        log_file = tmp_path / "timed.log"
        handler = CompressedTimedRotatingFileHandler(
            str(log_file), when="S", interval=1, backupCount=2
        )
        try:
            handler.stream.write("timed payload")
            handler.stream.flush()
            handler.doRollover()
        finally:
            handler.close()

        compressed = [
            name for name in os.listdir(tmp_path) if name.endswith(".gz")
        ]
        assert compressed
        with gzip.open(tmp_path / compressed[0], "rb") as handle:
            assert handle.read() == b"timed payload"
        assert not any(
            name.startswith("timed.log.") and not name.endswith(".gz")
            for name in os.listdir(tmp_path)
        )

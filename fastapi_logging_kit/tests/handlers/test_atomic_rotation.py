"""Gzip rollover should never publish corrupt partial archives."""
import gzip
from unittest.mock import patch

import pytest

from fastapi_logging_kit.handlers.rotating_file_handler import _gzip_rotator


def test_partial_copy_failure_keeps_source_and_cleans_temporary(tmp_path):
    src = tmp_path / "service.log"
    dest = tmp_path / "service.log.1.gz"
    src.write_bytes(b"important data")
    with patch(
        "fastapi_logging_kit.handlers.rotating_file_handler.shutil.copyfileobj",
        side_effect=OSError("disk full"),
    ), pytest.raises(OSError, match="disk full"):
        _gzip_rotator(str(src), str(dest))
    assert src.read_bytes() == b"important data"
    assert not dest.exists()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["service.log"]


def test_successful_compression_publishes_archive(tmp_path):
    src = tmp_path / "service.log"
    dest = tmp_path / "service.log.1.gz"
    src.write_bytes(b"readable data")
    _gzip_rotator(str(src), str(dest))
    assert not src.exists()
    with gzip.open(dest, "rb") as archive:
        assert archive.read() == b"readable data"


def test_rotator_accepts_uncompressed_destination_name(tmp_path):
    src = tmp_path / "service.log"
    dest = tmp_path / "service.log.1"
    src.write_bytes(b"hello")
    _gzip_rotator(str(src), str(dest))
    with gzip.open(str(dest) + ".gz", "rb") as archive:
        assert archive.read() == b"hello"


def test_atomic_replace_failure_retains_original(tmp_path):
    src = tmp_path / "service.log"
    dest = tmp_path / "service.log.1.gz"
    src.write_bytes(b"preserved")
    with patch("fastapi_logging_kit.handlers.rotating_file_handler.os.replace", side_effect=OSError("cannot rename")), pytest.raises(OSError):
        _gzip_rotator(str(src), str(dest))
    assert src.read_bytes() == b"preserved"
    assert not dest.exists()
    assert len(list(tmp_path.iterdir())) == 1

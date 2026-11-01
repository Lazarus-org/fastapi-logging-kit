"""Custom rotating file handlers that optionally gzip rotated log files."""

import gzip
import os
import shutil
import tempfile
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from typing import Any


def _gzip_namer(default_name: str) -> str:
    """Return the rotated filename with a .gz suffix appended."""
    return default_name + ".gz"


def _gzip_rotator(source: str, dest: str) -> None:
    """Atomically publish a complete gzip archive, preserving source on failure.

    Standard RotatingFileHandler is not safe for concurrent multi- process writes.
    """
    gz_dest = dest if dest.endswith(".gz") else dest + ".gz"
    fd, temporary = tempfile.mkstemp(
        prefix=".fastapi-logging-kit-", suffix=".tmp", dir=os.path.dirname(gz_dest)
    )
    try:
        with os.fdopen(fd, "wb") as raw:
            with gzip.GzipFile(fileobj=raw, mode="wb") as compressed:
                with open(source, "rb") as original:
                    shutil.copyfileobj(original, compressed)
        os.replace(temporary, gz_dest)
        os.remove(source)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class CompressedRotatingFileHandler(RotatingFileHandler):
    """RotatingFileHandler that gzip-compresses each rotated log file."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.rotator = _gzip_rotator
        self.namer = _gzip_namer


class CompressedTimedRotatingFileHandler(TimedRotatingFileHandler):
    """TimedRotatingFileHandler that gzip-compresses each rotated log file."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.rotator = _gzip_rotator
        self.namer = _gzip_namer

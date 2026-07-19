import os
import sys
import tarfile
import zipfile
from typing import Any, List

import pytest

from fast_logging.commands.archive_logs import BUNDLE_FORMATS, run
from fast_logging.settings import settings_manager
from fast_logging.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON

pytestmark = [
    pytest.mark.commands,
    pytest.mark.commands_archive_logs,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


def _archive_subdirs(log_dir: str) -> List[str]:
    """Return the timestamped subdirectories inside ``<log_dir>/archive``."""
    archive_root = os.path.join(log_dir, "archive")
    if not os.path.isdir(archive_root):
        return []
    return sorted(
        os.path.join(archive_root, name) for name in os.listdir(archive_root)
    )


class TestArchiveLogsCommand:
    """Test suite for the `archive_logs` command."""

    def test_supported_bundle_formats(self) -> None:
        """Test that the supported bundle formats are tar.gz and zip."""
        assert BUNDLE_FORMATS == ("tar.gz", "zip")

    def test_missing_log_directory(self, tmp_path: Any) -> None:
        """Test that a missing log directory reports an error and stops."""
        missing = str(tmp_path / "nope")
        settings_manager.load({"LOG_DIR": missing})

        out = run(echo=False)

        assert f"Log directory not found: {missing}" in out.getvalue()

    def test_no_rotated_files(self, temp_log_directory: str) -> None:
        """Test that a directory holding only active logs archives nothing."""
        with open(os.path.join(temp_log_directory, "info.log"), "wb") as file:
            file.write(b"active\n")
        settings_manager.load({"LOG_DIR": temp_log_directory})

        out = run(echo=False)

        assert "No rotated log files found." in out.getvalue()
        assert _archive_subdirs(temp_log_directory) == []

    def test_skips_existing_archive_directory(
        self, log_dir_with_rotated_files: str
    ) -> None:
        """Test that files already inside archive/ are not archived again."""
        previous = os.path.join(log_dir_with_rotated_files, "archive", "2020-01-01_000000")
        os.makedirs(previous, exist_ok=True)
        already_archived = os.path.join(previous, "old.log.9")
        with open(already_archived, "wb") as file:
            file.write(b"old\n")
        settings_manager.load({"LOG_DIR": log_dir_with_rotated_files})

        out = run(echo=False)

        assert "Archived 3 file(s)" in out.getvalue()
        assert os.path.exists(already_archived)

    def test_moves_rotated_files(self, log_dir_with_rotated_files: str) -> None:
        """Test that rotated files move into the archive and active logs stay."""
        settings_manager.load({"LOG_DIR": log_dir_with_rotated_files})

        out = run(echo=False)

        assert "Archived 3 file(s)" in out.getvalue()
        archived = os.listdir(_archive_subdirs(log_dir_with_rotated_files)[0])
        assert sorted(archived) == [
            "debug.log.1.gz",
            "error.log.2024-01-15",
            "info.log.1",
        ]
        # Active log files are never touched.
        assert os.path.exists(os.path.join(log_dir_with_rotated_files, "info.log"))
        assert os.path.exists(os.path.join(log_dir_with_rotated_files, "error.log"))

    def test_compress_gzips_uncompressed_files(
        self, log_dir_with_rotated_files: str
    ) -> None:
        """Test that --compress gzips files that are not already compressed."""
        settings_manager.load({"LOG_DIR": log_dir_with_rotated_files})

        run(echo=False, compress=True)

        archived = sorted(os.listdir(_archive_subdirs(log_dir_with_rotated_files)[0]))
        assert archived == [
            "debug.log.1.gz",
            "error.log.2024-01-15.gz",
            "info.log.1.gz",
        ]
        assert not os.path.exists(
            os.path.join(log_dir_with_rotated_files, "info.log.1")
        )

    def test_bundle_targz(self, log_dir_with_rotated_files: str) -> None:
        """Test that --bundle tar.gz produces a tarball and drops the directory."""
        settings_manager.load({"LOG_DIR": log_dir_with_rotated_files})

        out = run(echo=False, bundle="tar.gz")

        archive_root = os.path.join(log_dir_with_rotated_files, "archive")
        bundles = [n for n in os.listdir(archive_root) if n.endswith(".tar.gz")]
        assert len(bundles) == 1
        bundle_path = os.path.join(archive_root, bundles[0])
        assert tarfile.is_tarfile(bundle_path)
        assert _archive_subdirs(log_dir_with_rotated_files) == [bundle_path]
        assert "Bundled archive directory into" in out.getvalue()

    def test_bundle_zip(self, log_dir_with_rotated_files: str) -> None:
        """Test that --bundle zip produces a zip file and drops the directory."""
        settings_manager.load({"LOG_DIR": log_dir_with_rotated_files})

        out = run(echo=False, bundle="zip")

        archive_root = os.path.join(log_dir_with_rotated_files, "archive")
        bundles = [n for n in os.listdir(archive_root) if n.endswith(".zip")]
        assert len(bundles) == 1
        bundle_path = os.path.join(archive_root, bundles[0])
        assert zipfile.is_zipfile(bundle_path)
        with zipfile.ZipFile(bundle_path) as archive:
            assert any("info.log.1" in name for name in archive.namelist())
        assert _archive_subdirs(log_dir_with_rotated_files) == [bundle_path]
        assert "and removed the source directory." in out.getvalue()

    def test_dry_run_plain(self, log_dir_with_rotated_files: str) -> None:
        """Test that a dry run lists the files without moving them."""
        settings_manager.load({"LOG_DIR": log_dir_with_rotated_files})

        out = run(echo=False, dry_run=True)
        output = out.getvalue()

        assert "[DRY RUN] Would archive 3 file(s)" in output
        assert "Would then bundle" not in output
        assert _archive_subdirs(log_dir_with_rotated_files) == []
        assert os.path.exists(os.path.join(log_dir_with_rotated_files, "info.log.1"))

    def test_dry_run_with_compress_and_bundle(
        self, log_dir_with_rotated_files: str
    ) -> None:
        """Test that a dry run announces gzipping and bundling without acting."""
        settings_manager.load({"LOG_DIR": log_dir_with_rotated_files})

        out = run(echo=False, compress=True, bundle="zip", dry_run=True)
        output = out.getvalue()

        assert "(+ gzip)" in output
        assert "[DRY RUN] Would then bundle the directory into:" in output
        assert ".zip" in output
        assert _archive_subdirs(log_dir_with_rotated_files) == []

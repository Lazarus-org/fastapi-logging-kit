import os
import sys
from typing import Any, List
from unittest.mock import MagicMock

import pytest

from fast_logging.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON
from fast_logging.utils.command.process_file import process_files, setup_directories

pytestmark = [
    pytest.mark.utils,
    pytest.mark.utils_process_file,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


class TestSetupDirectories:
    """Test suite for the `setup_directories` helper."""

    def test_raises_for_missing_log_directory(self, tmp_path: Any) -> None:
        """Test that a missing log directory raises FileNotFoundError."""
        missing = str(tmp_path / "nope")

        with pytest.raises(FileNotFoundError, match="does not exist"):
            setup_directories(missing, "json")

    def test_raises_for_missing_subdirectory(self, temp_log_directory: str) -> None:
        """Test that a missing subdirectory raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="json"):
            setup_directories(temp_log_directory, "json")

    def test_creates_pretty_directory(self, temp_json_log_directory: str) -> None:
        """Test that the pretty subdirectory is created and both paths returned."""
        sub_dir, pretty_dir = setup_directories(temp_json_log_directory, "json")

        assert sub_dir == os.path.join(temp_json_log_directory, "json")
        assert pretty_dir == os.path.join(sub_dir, "pretty")
        assert os.path.isdir(pretty_dir)

    def test_is_idempotent(self, temp_json_log_directory: str) -> None:
        """Test that calling twice does not fail on the existing pretty directory."""
        first = setup_directories(temp_json_log_directory, "json")
        second = setup_directories(temp_json_log_directory, "json")

        assert first == second


class TestProcessFiles:
    """Test suite for the `process_files` generator."""

    def test_yields_only_matching_extension(self, temp_log_directory: str) -> None:
        """Test that only files with the requested extension are yielded."""
        for name in ("a.json", "b.json", "c.txt"):
            with open(
                os.path.join(temp_log_directory, name), "w", encoding="utf-8"
            ) as file:
                file.write("{}")

        results: List[str] = [
            filename
            for _, filename in process_files(
                temp_log_directory, ".json", MagicMock()
            )
        ]

        assert sorted(results) == ["a.json", "b.json"]

    def test_yields_full_paths(self, temp_log_directory: str) -> None:
        """Test that the yielded path joins the directory and the filename."""
        path = os.path.join(temp_log_directory, "only.xml")
        with open(path, "w", encoding="utf-8") as file:
            file.write("<log/>")

        assert list(process_files(temp_log_directory, ".xml", MagicMock())) == [
            (path, "only.xml")
        ]

    def test_yields_nothing_when_no_match(self, temp_log_directory: str) -> None:
        """Test that an empty directory yields no files."""
        assert list(process_files(temp_log_directory, ".json", MagicMock())) == []

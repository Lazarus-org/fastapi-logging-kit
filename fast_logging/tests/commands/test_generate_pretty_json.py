import json
import os
import sys
from typing import Any

import pytest

from fast_logging.commands.generate_pretty_json import run
from fast_logging.settings import settings_manager
from fast_logging.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON

pytestmark = [
    pytest.mark.commands,
    pytest.mark.commands_generate_pretty_json,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


class TestGeneratePrettyJsonCommand:
    """Test suite for the `generate_pretty_json` command."""

    def test_missing_json_directory(self, temp_log_directory: str) -> None:
        """Test that an absent json subdirectory reports an error and stops."""
        settings_manager.load({"LOG_DIR": temp_log_directory})

        out = run(echo=False)

        assert "does not exist." in out.getvalue()

    def test_reformats_json_file(self, temp_json_log_directory: str) -> None:
        """Test that a log file of JSON objects becomes a pretty JSON array."""
        settings_manager.load({"LOG_DIR": temp_json_log_directory})

        out = run(echo=False)
        output = out.getvalue()

        assert "Processing file:" in output
        assert "File test.json reformatted" in output

        pretty_path = os.path.join(
            temp_json_log_directory, "json", "pretty", "formatted_test.json"
        )
        with open(pretty_path, encoding="utf-8") as file:
            parsed = json.load(file)

        assert parsed == [{"message": "first"}, {"message": "second"}]

    def test_reports_incomplete_json_object(
        self, temp_json_log_directory: str, tmp_path: Any
    ) -> None:
        """Test that a trailing partial JSON object is reported as incomplete."""
        json_dir = os.path.join(temp_json_log_directory, "json")
        with open(os.path.join(json_dir, "test.json"), "w", encoding="utf-8") as file:
            file.write('{"message": "first"}\n\n{"message": "unterminated"\n')
        settings_manager.load({"LOG_DIR": temp_json_log_directory})

        out = run(echo=False)

        assert 'Incomplete JSON object: {"message": "unterminated"' in out.getvalue()

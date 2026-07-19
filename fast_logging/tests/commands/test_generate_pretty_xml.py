import os
import sys

import pytest

from fast_logging.commands.generate_pretty_xml import run
from fast_logging.settings import settings_manager
from fast_logging.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON

pytestmark = [
    pytest.mark.commands,
    pytest.mark.commands_generate_pretty_xml,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


class TestGeneratePrettyXmlCommand:
    """Test suite for the `generate_pretty_xml` command."""

    def test_missing_xml_directory(self, temp_log_directory: str) -> None:
        """Test that an absent xml subdirectory reports an error and stops."""
        settings_manager.load({"LOG_DIR": temp_log_directory})

        out = run(echo=False)

        assert "does not exist." in out.getvalue()

    def test_reformats_xml_file(self, temp_xml_log_directory: str) -> None:
        """Test that the XML content is wrapped in a <logs> element."""
        xml_dir = os.path.join(temp_xml_log_directory, "xml")
        with open(os.path.join(xml_dir, "test.xml"), "a", encoding="utf-8") as file:
            file.write("\n<log><message>second</message></log>\n")
        settings_manager.load({"LOG_DIR": temp_xml_log_directory})

        out = run(echo=False)
        output = out.getvalue()

        assert "Processing file:" in output
        assert "File test.xml reformatted successfully." in output

        pretty_path = os.path.join(xml_dir, "pretty", "formatted_test.xml")
        with open(pretty_path, encoding="utf-8") as file:
            content = file.read()

        assert content.startswith("<logs>\n")
        assert content.endswith("</logs>\n")
        assert "<message>hello</message>" in content
        assert "<message>second</message>" in content

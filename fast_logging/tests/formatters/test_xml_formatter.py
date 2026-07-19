import logging
import sys
import xml.etree.ElementTree as ET  # nosec B405

import pytest

from fast_logging.formatters import XMLFormatter
from fast_logging.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON

pytestmark = [
    pytest.mark.formatters,
    pytest.mark.xml_formatter,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


class TestXMLFormatterFormat:
    """Test suite for `XMLFormatter.format`."""

    def test_formats_record_as_valid_xml(
        self, xml_formatter: XMLFormatter, info_log_record: logging.LogRecord
    ) -> None:
        """Test that the output parses as XML rooted at a `log` element."""
        root = ET.fromstring(xml_formatter.format(info_log_record))  # nosec B314
        assert root.tag == "log"
        assert root.find("levelname").text == "INFO"
        assert root.find("message").text == "This is an info message"
        assert root.find("asctime") is not None

    def test_output_is_pretty_printed(
        self, xml_formatter: XMLFormatter, info_log_record: logging.LogRecord
    ) -> None:
        """Test that the XML is indented and stripped of the XML declaration."""
        output = xml_formatter.format(info_log_record)
        assert output.startswith("<log>")
        assert "<?xml" not in output
        assert "\n  <levelname>" in output

    def test_skips_none_values(self, info_log_record: logging.LogRecord) -> None:
        """Test that specifiers resolving to `None` produce no element."""
        formatter = XMLFormatter(fmt="%(levelname)s | %(missing_field)s")
        root = ET.fromstring(formatter.format(info_log_record))  # nosec B314
        assert root.find("missing_field") is None
        assert root.find("levelname") is not None

    def test_skips_empty_string_values(
        self, info_log_record: logging.LogRecord
    ) -> None:
        """Test that specifiers resolving to an empty string produce no element."""
        info_log_record.blank_field = ""
        formatter = XMLFormatter(fmt="%(levelname)s | %(blank_field)s")
        root = ET.fromstring(formatter.format(info_log_record))  # nosec B314
        assert root.find("blank_field") is None

    def test_includes_exception_element(
        self, xml_formatter: XMLFormatter, error_with_exc_log_record: logging.LogRecord
    ) -> None:
        """Test that an `exception` element is added when `exc_info` is present."""
        root = ET.fromstring(  # nosec B314
            xml_formatter.format(error_with_exc_log_record)
        )
        assert "ValueError: Something went wrong" in root.find("exception").text

    def test_omits_exception_element_when_absent(
        self, xml_formatter: XMLFormatter, error_log_record: logging.LogRecord
    ) -> None:
        """Test that no `exception` element is added without `exc_info`."""
        root = ET.fromstring(xml_formatter.format(error_log_record))  # nosec B314
        assert root.find("exception") is None


class TestXMLFormatterComplexValues:
    """Test suite for complex value rendering in `XMLFormatter`."""

    def test_renders_dict_value_as_nested_elements(
        self, info_log_record: logging.LogRecord
    ) -> None:
        """Test that dict values become nested child elements keyed by dict key."""
        info_log_record.context = {"user": "bob", "attempts": 3}
        formatter = XMLFormatter(fmt="%(context)s")
        root = ET.fromstring(formatter.format(info_log_record))  # nosec B314
        context = root.find("context")
        assert context.find("user").text == "bob"
        assert context.find("attempts").text == "3"

    def test_renders_list_value_as_indexed_elements(
        self, info_log_record: logging.LogRecord
    ) -> None:
        """Test that list values become `item_N` child elements."""
        info_log_record.tags = ["alpha", "beta"]
        formatter = XMLFormatter(fmt="%(tags)s")
        root = ET.fromstring(formatter.format(info_log_record))  # nosec B314
        tags = root.find("tags")
        assert tags.find("item_0").text == "alpha"
        assert tags.find("item_1").text == "beta"

    def test_renders_tuple_value_as_indexed_elements(
        self, info_log_record: logging.LogRecord
    ) -> None:
        """Test that tuple values also become `item_N` child elements."""
        info_log_record.point = (1, 2)
        formatter = XMLFormatter(fmt="%(point)s")
        root = ET.fromstring(formatter.format(info_log_record))  # nosec B314
        point = root.find("point")
        assert point.find("item_0").text == "1"
        assert point.find("item_1").text == "2"

    def test_add_field_to_xml_handles_tuple_directly(
        self, xml_formatter: XMLFormatter
    ) -> None:
        """Test that `_add_field_to_xml` indexes a raw tuple value."""
        parent = ET.Element("log")
        xml_formatter._add_field_to_xml(parent, "coords", (7, 8))
        coords = parent.find("coords")
        assert [child.tag for child in coords] == ["item_0", "item_1"]

    def test_add_field_to_xml_handles_scalar(
        self, xml_formatter: XMLFormatter
    ) -> None:
        """Test that `_add_field_to_xml` stringifies a scalar value into the text."""
        parent = ET.Element("log")
        xml_formatter._add_field_to_xml(parent, "count", 5)
        assert parent.find("count").text == "5"

import sys

import pytest

from fast_logging.templating import (
    STATIC_URL_PREFIX,
    environment,
    render_to_string,
    static_url,
)
from fast_logging.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON

pytestmark = [
    pytest.mark.utils,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


class TestStaticUrl:
    """Test suite for :func:`static_url`."""

    def test_relative_path(self) -> None:
        """Test that a relative asset path is prefixed with the static URL."""
        assert static_url("LogiBoard/css/app.css") == (
            f"{STATIC_URL_PREFIX}/LogiBoard/css/app.css"
        )

    def test_leading_slash_is_stripped(self) -> None:
        """Test that a leading slash does not produce a doubled separator."""
        assert static_url("/LogiBoard/css/app.css") == (
            f"{STATIC_URL_PREFIX}/LogiBoard/css/app.css"
        )


class TestEnvironment:
    """Test suite for the packaged Jinja2 environment."""

    def test_static_global_is_registered(self) -> None:
        """Test that the environment exposes ``static`` as a global."""
        assert environment.globals["static"] is static_url


class TestRenderToString:
    """Test suite for :func:`render_to_string`."""

    def test_renders_packaged_template_with_context(self) -> None:
        """Test that a packaged template renders with the supplied context."""
        rendered = render_to_string(
            "email_notifier_template.html",
            {
                "message": "a log entry",
                "date": "01 JANUARY 2026",
                "time": "10:30 AM",
                "browser_type": "TestBrowser/1.0",
                "ip_address": "10.0.0.7",
            },
        )

        assert "a log entry" in rendered
        assert "01 JANUARY 2026" in rendered
        assert "10:30 AM" in rendered
        assert "TestBrowser/1.0" in rendered
        assert "10.0.0.7" in rendered

    def test_renders_without_context(self) -> None:
        """Test that omitting the context still renders the template."""
        rendered = render_to_string("email_notifier_template.html")

        assert "This is an automated message." in rendered

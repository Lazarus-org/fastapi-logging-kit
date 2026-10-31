import sys
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from fastapi_logging_kit.commands.cli import app, main
from fastapi_logging_kit.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON

pytestmark = [
    pytest.mark.commands,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]

runner = CliRunner()


class TestCli:
    """Test suite for the `fastapi-logging-kit` Typer application."""

    def test_no_args_shows_help(self) -> None:
        """Test that invoking the app without arguments prints the help."""
        result = runner.invoke(app, [])

        assert "Maintenance commands" in result.output

    def test_send_logs(self) -> None:
        """Test that send-logs forwards the email address to the command."""
        with patch(
            "fastapi_logging_kit.commands.send_logs.run", new=MagicMock()
        ) as mock_run:
            result = runner.invoke(app, ["send-logs", "ops@example.com"])

        assert result.exit_code == 0
        mock_run.assert_called_once_with(email="ops@example.com")

    def test_archive_logs_defaults(self) -> None:
        """Test that archive-logs passes its default flag values through."""
        with patch(
            "fastapi_logging_kit.commands.archive_logs.run", new=MagicMock()
        ) as mock_run:
            result = runner.invoke(app, ["archive-logs"])

        assert result.exit_code == 0
        mock_run.assert_called_once_with(compress=False, bundle=None, dry_run=False)

    def test_archive_logs_with_options(self) -> None:
        """Test that archive-logs forwards --compress, --bundle and --dry-run."""
        with patch(
            "fastapi_logging_kit.commands.archive_logs.run", new=MagicMock()
        ) as mock_run:
            result = runner.invoke(
                app, ["archive-logs", "--compress", "--bundle", "zip", "--dry-run"]
            )

        assert result.exit_code == 0
        mock_run.assert_called_once_with(compress=True, bundle="zip", dry_run=True)

    def test_archive_logs_rejects_unknown_bundle_format(self) -> None:
        """Test that an unsupported --bundle value is rejected."""
        with patch(
            "fastapi_logging_kit.commands.archive_logs.run", new=MagicMock()
        ) as mock_run:
            result = runner.invoke(app, ["archive-logs", "--bundle", "badformat"])

        assert result.exit_code != 0
        assert "is not a supported bundle format" in result.output
        mock_run.assert_not_called()

    def test_logs_size_audit(self) -> None:
        """Test that logs-size-audit runs the underlying command."""
        with patch(
            "fastapi_logging_kit.commands.logs_size_audit.run", new=MagicMock()
        ) as mock_run:
            result = runner.invoke(app, ["logs-size-audit"])

        assert result.exit_code == 0
        mock_run.assert_called_once_with()

    def test_rotate_logs(self) -> None:
        """Test that rotate-logs runs the underlying command."""
        with patch(
            "fastapi_logging_kit.commands.rotate_logs.run", new=MagicMock()
        ) as mock_run:
            result = runner.invoke(app, ["rotate-logs"])

        assert result.exit_code == 0
        mock_run.assert_called_once_with()

    def test_generate_pretty_json(self) -> None:
        """Test that generate-pretty-json runs the underlying command."""
        with patch(
            "fastapi_logging_kit.commands.generate_pretty_json.run", new=MagicMock()
        ) as mock_run:
            result = runner.invoke(app, ["generate-pretty-json"])

        assert result.exit_code == 0
        mock_run.assert_called_once_with()

    def test_generate_pretty_xml(self) -> None:
        """Test that generate-pretty-xml runs the underlying command."""
        with patch(
            "fastapi_logging_kit.commands.generate_pretty_xml.run", new=MagicMock()
        ) as mock_run:
            result = runner.invoke(app, ["generate-pretty-xml"])

        assert result.exit_code == 0
        mock_run.assert_called_once_with()

    def test_main_invokes_app(self) -> None:
        """Test that the console script entry point runs the Typer app."""
        with patch("fastapi_logging_kit.commands.cli.app") as mock_app:
            main()

        mock_app.assert_called_once_with()

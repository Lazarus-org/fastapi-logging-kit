import sys

import pytest

from fast_logging.commands.base import (
    BaseCommand,
    OutputWrapper,
    Style,
    build_runner,
)
from fast_logging.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON

pytestmark = [
    pytest.mark.commands,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


class TestStyle:
    """Test suite for the `Style` helper class."""

    def test_success(self) -> None:
        """Test that SUCCESS returns a string containing the message."""
        assert "done" in Style.SUCCESS("done")

    def test_error(self) -> None:
        """Test that ERROR returns a string containing the message."""
        assert "boom" in Style.ERROR("boom")

    def test_warning(self) -> None:
        """Test that WARNING returns a string containing the message."""
        assert "careful" in Style.WARNING("careful")

    def test_notice(self) -> None:
        """Test that NOTICE returns a string containing the message."""
        assert "notice" in Style.NOTICE("notice")

    def test_http_info(self) -> None:
        """Test that HTTP_INFO returns a string containing the message."""
        assert "info" in Style.HTTP_INFO("info")


class TestOutputWrapper:
    """Test suite for the `OutputWrapper` class."""

    def test_records_lines_without_echo(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """Test that writes are recorded but not printed when echo is False."""
        wrapper = OutputWrapper(echo=False)
        wrapper.write("first")
        wrapper.write("second")

        assert wrapper.lines == ["first", "second"]
        assert capsys.readouterr().out == ""

    def test_echoes_when_enabled(self, capsys: pytest.CaptureFixture) -> None:
        """Test that writes are printed when echo is True."""
        wrapper = OutputWrapper(echo=True)
        wrapper.write("printed")

        assert "printed" in capsys.readouterr().out
        assert wrapper.lines == ["printed"]

    def test_getvalue_joins_lines(self) -> None:
        """Test that getvalue joins every written line with newlines."""
        wrapper = OutputWrapper(echo=False)
        wrapper.write("a")
        wrapper.write("b")

        assert wrapper.getvalue() == "a\nb"

    def test_getvalue_empty(self) -> None:
        """Test that getvalue returns an empty string when nothing was written."""
        assert OutputWrapper(echo=False).getvalue() == ""


class TestBaseCommand:
    """Test suite for the `BaseCommand` class."""

    def test_creates_wrapper_implicitly(self) -> None:
        """Test that a command builds its own output wrapper when none is given."""
        command = BaseCommand(echo=False)

        assert isinstance(command.stdout, OutputWrapper)
        assert command.stdout.echo is False
        assert isinstance(command.style, Style)

    def test_accepts_supplied_wrapper(self) -> None:
        """Test that an explicitly supplied output wrapper is used as-is."""
        wrapper = OutputWrapper(echo=False)
        command = BaseCommand(stdout=wrapper)

        assert command.stdout is wrapper

    def test_handle_raises_not_implemented(self) -> None:
        """Test that the base handle implementation refuses to run."""
        with pytest.raises(NotImplementedError):
            BaseCommand(echo=False).handle()

    def test_help_defaults_to_empty(self) -> None:
        """Test that the base command declares an empty help string."""
        assert BaseCommand.help == ""


class TestBuildRunner:
    """Test suite for the `build_runner` factory."""

    def test_runs_command_and_returns_wrapper(self) -> None:
        """Test that the runner calls handle and returns the output wrapper."""

        class DummyCommand(BaseCommand):
            """A command recording the arguments it was handed."""

            def handle(self, *args: object, **kwargs: object) -> None:
                """Write the received arguments to stdout."""
                self.stdout.write(f"{args}|{kwargs}")

        run = build_runner(DummyCommand)
        out = run("positional", echo=False, key="value")

        assert isinstance(out, OutputWrapper)
        assert out.getvalue() == "('positional',)|{'key': 'value'}"

    def test_propagates_not_implemented(self) -> None:
        """Test that a command without a handle implementation raises."""
        run = build_runner(BaseCommand)

        with pytest.raises(NotImplementedError):
            run(echo=False)

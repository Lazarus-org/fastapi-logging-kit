"""Shared plumbing for the ``fastapi_logging_kit`` CLI commands.

``django_logging`` shipped its commands as Django management commands,
which gave them ``self.stdout.write`` and ``self.style.SUCCESS(...)``.
FastAPI projects have no ``manage.py``, so the equivalents here are
plain callables exposed through a Typer application.

Each command module defines a ``run()`` function holding all the logic,
so the commands can be tested directly without going through the CLI.

"""

from typing import Any, Callable, List, Optional

import typer


class Style:
    """ANSI styling helpers mirroring Django's ``self.style``.

    Each method wraps its argument in the colour Django uses for the
    same message class, so ported command bodies keep reading the same.

    """

    @staticmethod
    def SUCCESS(message: str) -> str:
        """Style *message* as a success."""
        return typer.style(message, fg=typer.colors.GREEN)

    @staticmethod
    def ERROR(message: str) -> str:
        """Style *message* as an error."""
        return typer.style(message, fg=typer.colors.RED, bold=True)

    @staticmethod
    def WARNING(message: str) -> str:
        """Style *message* as a warning."""
        return typer.style(message, fg=typer.colors.YELLOW)

    @staticmethod
    def NOTICE(message: str) -> str:
        """Style *message* as a notice."""
        return typer.style(message, fg=typer.colors.CYAN)

    @staticmethod
    def HTTP_INFO(message: str) -> str:
        """Style *message* as informational output."""
        return typer.style(message, fg=typer.colors.BRIGHT_BLUE)


class OutputWrapper:
    """A tiny stand-in for Django's ``self.stdout``.

    Collects everything written so tests can assert on command output
    without capturing the process stdout.

    Attributes:
        lines (List[str]): Every message written through this wrapper.
        echo (bool): Whether messages are also printed to the terminal.

    """

    def __init__(self, echo: bool = True) -> None:
        """Initialize the wrapper.

        Args:
            echo (bool): Whether to print messages as they are written.

        """
        self.lines: List[str] = []
        self.echo = echo

    def write(self, message: str) -> None:
        """Record and optionally print *message*.

        Args:
            message (str): The message to write.

        """
        self.lines.append(message)
        if self.echo:
            typer.echo(message)

    def getvalue(self) -> str:
        """Return everything written so far, newline-joined.

        Returns:
            str: The accumulated output.

        """
        return "\n".join(self.lines)


class BaseCommand:
    """Base class for the ported commands.

    Provides the ``stdout``/``style`` attributes the Django command
    bodies were written against.

    Attributes:
        stdout (OutputWrapper): Where command output is written.
        style (Style): The styling helpers.

    """

    help: str = ""

    def __init__(self, stdout: Optional[OutputWrapper] = None, echo: bool = True) -> None:
        """Initialize the command.

        Args:
            stdout (Optional[OutputWrapper]): An output wrapper to use.
            echo (bool): Whether output is printed when creating a
                wrapper implicitly.

        """
        self.stdout = stdout if stdout is not None else OutputWrapper(echo=echo)
        self.style = Style()

    def handle(self, *args: Any, **kwargs: Any) -> Any:
        """Run the command.

        Args:
            *args (Any): Positional arguments.
            **kwargs (Any): Keyword arguments.

        Raises:
            NotImplementedError: Always, unless overridden by a subclass.

        """
        raise NotImplementedError("handle must be implemented by subclass")


def build_runner(command_class: Callable[..., BaseCommand]) -> Callable[..., OutputWrapper]:
    """Return a ``run()`` callable that instantiates and runs a command.

    Args:
        command_class (Callable[..., BaseCommand]): The command class.

    Returns:
        Callable[..., OutputWrapper]: A function running the command and
        returning its output wrapper.

    """

    def run(*args: Any, echo: bool = True, **kwargs: Any) -> OutputWrapper:
        command = command_class(echo=echo)
        command.handle(*args, **kwargs)
        return command.stdout

    return run

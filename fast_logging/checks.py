"""A minimal re-implementation of the Django system-check framework.

``django_logging`` validates its configuration through Django's system
checks (``django.core.checks``): validators return ``Error`` instances,
functions decorated with ``@register()`` are collected into a registry,
and Django runs them at startup.

FastAPI has no such framework, so ``fast_logging`` ships an equivalent
that is deliberately tiny: an :class:`Error` message object, a
:func:`register` decorator backed by a module-level registry, and
:func:`run_checks` which executes every registered check and returns the
combined list of errors.

Unlike Django — which aborts startup on any error — ``fast_logging``
reports check failures as warnings on the ``fast_logging`` logger so a
misconfigured application still boots with a usable default
configuration. Call :func:`run_checks` directly if you would rather fail
loudly.

"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

CheckFunction = Callable[..., List["Error"]]

# Every check registered through @register() lands here.
registry: List[CheckFunction] = []


@dataclass
class CheckMessage:
    """A single message produced by a configuration check.

    Attributes:
        msg (str): The human-readable description of the problem.
        hint (Optional[str]): An optional suggestion for fixing it.
        id (Optional[str]): A stable identifier such as ``fast_logging.E001``.
        level (str): The severity of the message.

    """

    msg: str
    hint: Optional[str] = None
    id: Optional[str] = None
    level: str = field(default="ERROR")

    def __str__(self) -> str:
        """Render the message the way Django renders check messages."""
        prefix = f"({self.id}) " if self.id else ""
        suffix = f"\n\tHINT: {self.hint}" if self.hint else ""
        return f"{prefix}{self.msg}{suffix}"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: level={self.level!r}, msg={self.msg!r}>"

    def is_serious(self) -> bool:
        """Return ``True`` when this message represents an error."""
        return self.level == "ERROR"


@dataclass(repr=False)
class Error(CheckMessage):
    """An ``ERROR``-level check message.

    Mirrors ``django.core.checks.Error`` closely enough that the
    validator code ported from ``django_logging`` needs no changes.

    """

    level: str = field(default="ERROR")


@dataclass(repr=False)
class Warning(CheckMessage):  # pylint: disable=redefined-builtin
    """A ``WARNING``-level check message."""

    level: str = field(default="WARNING")


def register(check: Optional[CheckFunction] = None) -> Any:
    """Register a configuration check.

    Supports both ``@register`` and ``@register()`` spellings so the
    decorator reads the same as Django's.

    Args:
        check (Optional[CheckFunction]): The check function, when used
            as a bare decorator.

    Returns:
        Any: The decorated function, or a decorator when called with
        parentheses.

    """

    def inner(func: CheckFunction) -> CheckFunction:
        if func not in registry:
            registry.append(func)
        return func

    if check is None:
        return inner
    return inner(check)


def run_checks(app_configs: Optional[Dict[str, Any]] = None, **kwargs: Any) -> List[Error]:
    """Run every registered check and return the combined errors.

    Args:
        app_configs (Optional[Dict[str, Any]]): Passed through to each
            check for signature compatibility with Django.
        **kwargs (Any): Extra keyword arguments forwarded to each check.

    Returns:
        List[Error]: Every error reported by the registered checks.

    """
    errors: List[Error] = []
    for check in registry:
        errors.extend(check(app_configs, **kwargs))
    return errors

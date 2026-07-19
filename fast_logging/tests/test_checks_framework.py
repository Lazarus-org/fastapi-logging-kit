import sys
from typing import Any, Dict, List

import pytest

from fast_logging.checks import (
    CheckMessage,
    Error,
    Warning,
    register,
    run_checks,
)
from fast_logging.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON

pytestmark = [
    pytest.mark.settings,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


class TestCheckMessage:
    """Test suite for the `CheckMessage` dataclass."""

    def test_str_includes_id_and_hint(self) -> None:
        """Test that rendering includes the id prefix and hint suffix."""
        message = CheckMessage("Something is wrong.", hint="Fix it.", id="pkg.E001")

        assert str(message) == "(pkg.E001) Something is wrong.\n\tHINT: Fix it."

    def test_str_without_id_or_hint(self) -> None:
        """Test that rendering omits the prefix and suffix when unset."""
        assert str(CheckMessage("Bare message.")) == "Bare message."

    def test_str_with_id_only(self) -> None:
        """Test that rendering includes only the id when there is no hint."""
        assert str(CheckMessage("Msg.", id="pkg.E002")) == "(pkg.E002) Msg."

    def test_str_with_hint_only(self) -> None:
        """Test that rendering includes only the hint when there is no id."""
        assert str(CheckMessage("Msg.", hint="Do this.")) == "Msg.\n\tHINT: Do this."

    def test_repr_shows_level_and_message(self) -> None:
        """Test that repr reports the class name, level and message."""
        assert repr(CheckMessage("Msg.")) == "<CheckMessage: level='ERROR', msg='Msg.'>"

    def test_default_level_is_error(self) -> None:
        """Test that the default severity is ERROR."""
        assert CheckMessage("Msg.").level == "ERROR"


class TestErrorAndWarning:
    """Test suite for the `Error` and `Warning` message subclasses."""

    def test_error_level_and_seriousness(self) -> None:
        """Test that an Error is ERROR-level and considered serious."""
        error = Error("Broken.", hint="Repair.", id="pkg.E003")

        assert error.level == "ERROR"
        assert error.is_serious() is True

    def test_error_repr_uses_subclass_name(self) -> None:
        """Test that repr on an Error names the Error class."""
        assert repr(Error("Broken.")) == "<Error: level='ERROR', msg='Broken.'>"

    def test_error_str(self) -> None:
        """Test that an Error renders like any other check message."""
        assert str(Error("Broken.", id="pkg.E003")) == "(pkg.E003) Broken."

    def test_warning_level_and_seriousness(self) -> None:
        """Test that a Warning is WARNING-level and not considered serious."""
        warning = Warning("Careful.")

        assert warning.level == "WARNING"
        assert warning.is_serious() is False

    def test_warning_repr_uses_subclass_name(self) -> None:
        """Test that repr on a Warning names the Warning class."""
        assert repr(Warning("Careful.")) == "<Warning: level='WARNING', msg='Careful.'>"

    def test_errors_compare_by_value(self) -> None:
        """Test that two Errors with identical fields are equal."""
        assert Error("Same.", id="pkg.E004") == Error("Same.", id="pkg.E004")


class TestRegister:
    """Test suite for the `register` decorator."""

    def test_register_with_parentheses(self, clean_check_registry: List[Any]) -> None:
        """Test that `@register()` adds the function to the registry."""
        clean_check_registry.clear()

        @register()
        def a_check(app_configs: Any, **kwargs: Any) -> List[Error]:
            return []

        assert clean_check_registry == [a_check]

    def test_register_bare(self, clean_check_registry: List[Any]) -> None:
        """Test that `@register` without parentheses also registers."""
        clean_check_registry.clear()

        @register
        def a_check(app_configs: Any, **kwargs: Any) -> List[Error]:
            return []

        assert clean_check_registry == [a_check]

    def test_register_returns_the_function(
        self, clean_check_registry: List[Any]
    ) -> None:
        """Test that the decorated function is returned unchanged."""
        clean_check_registry.clear()

        def a_check(app_configs: Any, **kwargs: Any) -> List[Error]:
            return [Error("from check")]

        assert register(a_check) is a_check
        assert a_check({}) == [Error("from check")]

    def test_registering_twice_does_not_duplicate(
        self, clean_check_registry: List[Any]
    ) -> None:
        """Test that registering the same function twice keeps a single entry."""
        clean_check_registry.clear()

        def a_check(app_configs: Any, **kwargs: Any) -> List[Error]:
            return []

        register(a_check)
        register(a_check)

        assert clean_check_registry == [a_check]


class TestRunChecks:
    """Test suite for `run_checks`."""

    def test_empty_registry_returns_no_errors(
        self, clean_check_registry: List[Any]
    ) -> None:
        """Test that an empty registry produces an empty error list."""
        clean_check_registry.clear()

        assert run_checks() == []

    def test_aggregates_errors_from_every_check(
        self, clean_check_registry: List[Any]
    ) -> None:
        """Test that errors from all registered checks are combined."""
        clean_check_registry.clear()

        @register()
        def first(app_configs: Any, **kwargs: Any) -> List[Error]:
            return [Error("first problem", id="pkg.E101")]

        @register()
        def second(app_configs: Any, **kwargs: Any) -> List[Error]:
            return [Error("second problem", id="pkg.E102")]

        @register()
        def clean(app_configs: Any, **kwargs: Any) -> List[Error]:
            return []

        errors = run_checks()

        assert [error.id for error in errors] == ["pkg.E101", "pkg.E102"]

    def test_passes_app_configs_and_kwargs_to_checks(
        self, clean_check_registry: List[Any]
    ) -> None:
        """Test that app_configs and extra kwargs reach each check."""
        clean_check_registry.clear()
        received: Dict[str, Any] = {}

        @register()
        def recording(app_configs: Any, **kwargs: Any) -> List[Error]:
            received["app_configs"] = app_configs
            received["kwargs"] = kwargs
            return []

        run_checks({"app": "config"}, extra="value")

        assert received["app_configs"] == {"app": "config"}
        assert received["kwargs"] == {"extra": "value"}

    def test_default_app_configs_is_none(
        self, clean_check_registry: List[Any]
    ) -> None:
        """Test that app_configs defaults to None when not supplied."""
        clean_check_registry.clear()
        seen: List[Any] = []

        @register()
        def recording(app_configs: Any, **kwargs: Any) -> List[Error]:
            seen.append(app_configs)
            return []

        run_checks()

        assert seen == [None]

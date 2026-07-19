import sys

import pytest

from fast_logging.contextvar import manager
from fast_logging.contextvar.contextvar_manager import ContextVarManager
from fast_logging.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON

pytestmark = [
    pytest.mark.contextvar,
    pytest.mark.contextvar_manager,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


class TestBinding:
    """Test suite for binding and unbinding context variables."""

    def test_bind_exposes_values(self) -> None:
        """Test that bound values show up in the retrieved contextvars."""
        manager.bind(request_id="abc", user="tester")

        assert manager.get_contextvars() == {"request_id": "abc", "user": "tester"}

    def test_bind_namespaces_the_variables(self) -> None:
        """Test that the underlying ContextVar names carry the package
        prefix."""
        manager.bind(request_id="abc")

        assert (
            f"{ContextVarManager.FAST_LOGGING_PREFIX}request_id"
            in manager._context_vars  # pylint: disable=protected-access
        )

    def test_get_or_create_reuses_the_same_variable(self) -> None:
        """Test that requesting the same key twice returns one ContextVar."""
        first = manager._get_or_create("request_id")  # pylint: disable=W0212
        second = manager._get_or_create("request_id")  # pylint: disable=W0212

        assert first is second

    def test_batch_bind_returns_tokens_for_reset(self) -> None:
        """Test that batch_bind tokens restore the previous values."""
        manager.bind(request_id="original")

        tokens = manager.batch_bind(request_id="temporary")
        assert manager.get_contextvars()["request_id"] == "temporary"

        manager.reset(tokens)
        assert manager.get_contextvars()["request_id"] == "original"

    def test_unbind_removes_the_value(self) -> None:
        """Test that unbinding a key hides it from the contextvars."""
        manager.bind(request_id="abc", user="tester")

        manager.unbind("request_id")

        assert manager.get_contextvars() == {"user": "tester"}

    def test_unbind_unknown_key_is_a_noop(self) -> None:
        """Test that unbinding a key that was never bound does nothing."""
        manager.bind(user="tester")

        manager.unbind("never_bound")

        assert manager.get_contextvars() == {"user": "tester"}

    def test_clear_removes_every_value(self) -> None:
        """Test that clear drops all bound context variables."""
        manager.bind(request_id="abc", user="tester")

        manager.clear()

        assert manager.get_contextvars() == {}


class TestContextRetrieval:
    """Test suite for retrieving and merging context dictionaries."""

    def test_get_contextvars_skips_unset_and_foreign_keys(self) -> None:
        """Test that unset values and non-prefixed variables are excluded."""
        import contextvars

        foreign = contextvars.ContextVar("unrelated", default=None)
        foreign.set("ignored")
        manager.bind(request_id="abc", user="tester")
        manager.unbind("user")

        assert manager.get_contextvars() == {"request_id": "abc"}

    def test_merge_contexts_prefers_bound_context(self) -> None:
        """Test that the bound context overrides the local context."""
        merged = manager.merge_contexts(
            {"key": "bound"}, {"key": "local", "other": "local-only"}
        )

        assert merged == {"key": "bound", "other": "local-only"}

    def test_get_merged_context_combines_both_sources(self) -> None:
        """Test that get_merged_context layers the bound context on top."""
        manager.bind(request_id="ambient", user="ambient-user")

        merged = manager.get_merged_context({"request_id": "bound"})

        assert merged == {"request_id": "bound", "user": "ambient-user"}


class TestScopedContext:
    """Test suite for the `scoped_context` context manager."""

    def test_restores_previous_values_on_exit(self) -> None:
        """Test that the previous values are restored when the block ends."""
        manager.bind(request_id="original")

        with manager.scoped_context(request_id="scoped"):
            assert manager.get_contextvars()["request_id"] == "scoped"

        assert manager.get_contextvars()["request_id"] == "original"

    def test_restores_previous_values_when_body_raises(self) -> None:
        """Test that the values are restored even if the block raises."""
        manager.bind(request_id="original")

        with pytest.raises(RuntimeError):
            with manager.scoped_context(request_id="scoped"):
                raise RuntimeError("boom")

        assert manager.get_contextvars()["request_id"] == "original"

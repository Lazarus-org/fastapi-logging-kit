import sys
import time

import pytest

import fast_logging.cache as cache_module
from fast_logging.cache import LocalMemoryCache, set_cache
from fast_logging.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON

pytestmark = [
    pytest.mark.utils,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]


class TestLocalMemoryCache:
    """Test suite for the `LocalMemoryCache` backend."""

    def test_set_and_get(self) -> None:
        """Test that a stored value is returned by `get`."""
        cache = LocalMemoryCache()
        cache.set("key", "value")
        assert cache.get("key") == "value"

    def test_get_missing_key_returns_default(self) -> None:
        """Test that a missing key yields the supplied default."""
        cache = LocalMemoryCache()
        assert cache.get("absent") is None
        assert cache.get("absent", "fallback") == "fallback"

    def test_set_without_timeout_never_expires(self) -> None:
        """Test that an entry stored without a timeout stays available."""
        cache = LocalMemoryCache()
        cache.set("key", 42, timeout=None)
        assert cache.get("key") == 42

    def test_entry_expires_after_timeout(self) -> None:
        """Test that an entry is dropped once its timeout has elapsed."""
        cache = LocalMemoryCache()
        cache.set("key", "value", timeout=0.01)
        assert cache.get("key") == "value"

        time.sleep(0.05)

        assert cache.get("key") is None
        assert cache.get("key", "default") == "default"

    def test_delete_removes_entry(self) -> None:
        """Test that `delete` removes a key and tolerates missing ones."""
        cache = LocalMemoryCache()
        cache.set("key", "value")
        cache.delete("key")
        assert cache.get("key") is None

        cache.delete("key")

    def test_clear_removes_every_entry(self) -> None:
        """Test that `clear` empties the whole cache."""
        cache = LocalMemoryCache()
        cache.set("one", 1)
        cache.set("two", 2)

        cache.clear()

        assert cache.get("one") is None
        assert cache.get("two") is None


class TestSetCache:
    """Test suite for the `set_cache` backend swapping helper."""

    def test_set_cache_replaces_backend(self) -> None:
        """Test that `set_cache` swaps the module level backend."""
        original = cache_module.cache
        replacement = LocalMemoryCache()

        try:
            set_cache(replacement)
            assert cache_module.cache is replacement

            cache_module.cache.set("key", "swapped")
            assert replacement.get("key") == "swapped"
        finally:
            set_cache(original)

        assert cache_module.cache is original

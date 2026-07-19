"""A minimal cache used to throttle periodic maintenance work.

``MonitorLogSizeMiddleware`` needs to remember when the log size audit
last ran. In ``django_logging`` that state lived in ``django.core.cache``;
FastAPI has no cache framework, so this module provides a small
in-process store with the same ``get``/``set`` interface.

The default backend is per-process, which is enough for the weekly audit
it guards. Applications running several workers can swap in a shared
backend — anything exposing ``get(key)`` and ``set(key, value,
timeout=None)`` — via :func:`set_cache`.

"""

import threading
import time
from typing import Any, Dict, Optional, Tuple


class LocalMemoryCache:
    """A thread-safe, in-process cache with optional per-key expiry."""

    def __init__(self) -> None:
        """Initialize an empty cache."""
        self._store: Dict[str, Tuple[Any, Optional[float]]] = {}
        self._lock = threading.Lock()

    def get(self, key: str, default: Any = None) -> Any:
        """Return the value stored under *key*.

        Args:
            key (str): The cache key.
            default (Any): Returned when the key is absent or expired.

        Returns:
            Any: The cached value, or ``default``.

        """
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return default

            value, expires_at = entry
            if expires_at is not None and expires_at <= time.time():
                del self._store[key]
                return default

            return value

    def set(self, key: str, value: Any, timeout: Optional[float] = None) -> None:
        """Store *value* under *key*.

        Args:
            key (str): The cache key.
            value (Any): The value to store.
            timeout (Optional[float]): Seconds until the entry expires.
                ``None`` means it never expires.

        """
        expires_at = time.time() + timeout if timeout is not None else None
        with self._lock:
            self._store[key] = (value, expires_at)

    def delete(self, key: str) -> None:
        """Remove *key* from the cache if present.

        Args:
            key (str): The cache key.

        """
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        """Remove every entry from the cache."""
        with self._lock:
            self._store.clear()


cache: Any = LocalMemoryCache()


def set_cache(backend: Any) -> None:
    """Replace the cache backend used by ``fast_logging``.

    Args:
        backend (Any): Any object exposing ``get(key, default)`` and
            ``set(key, value, timeout)``.

    """
    global cache  # pylint: disable=global-statement
    cache = backend

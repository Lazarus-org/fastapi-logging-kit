"""Context-local metadata used by FastAPI Logging Kit.

The manager owns only its own ContextVar instances. Scoped bindings use ContextVar
tokens so nested scopes and concurrent asyncio tasks restore their previous values
without clearing unrelated request or application context.
"""

import contextvars
from contextlib import contextmanager
from threading import RLock
from typing import Any, Dict, Generator

_UNSET = object()


class ContextVarManager:
    """Create, bind, retrieve and safely restore logging context variables."""

    FASTAPI_LOGGING_KIT_PREFIX = "fastapi_logging_kit_"

    def __init__(self) -> None:
        self._context_vars: Dict[str, contextvars.ContextVar[Any]] = {}
        self._lock = RLock()

    def _get_or_create(self, key: str) -> contextvars.ContextVar[Any]:
        """Return the package-owned ContextVar for *key*, creating it once."""
        if (
            not isinstance(key, str)
            or not key
            or key.startswith(self.FASTAPI_LOGGING_KIT_PREFIX)
        ):
            raise ValueError(
                "Context variable keys must be non-empty unprefixed strings."
            )
        full_key = f"{self.FASTAPI_LOGGING_KIT_PREFIX}{key}"
        with self._lock:
            variable = self._context_vars.get(full_key)
            if variable is None:
                variable = contextvars.ContextVar(full_key, default=_UNSET)
                self._context_vars[full_key] = variable
            return variable

    def bind(self, **kwargs: Any) -> None:
        """Bind values in the current execution context."""
        for key, value in kwargs.items():
            self._get_or_create(key).set(value)

    def batch_bind(self, **kwargs: Any) -> Dict[str, contextvars.Token]:
        """Bind values and return tokens that restore their previous values."""
        return {
            key: self._get_or_create(key).set(value) for key, value in kwargs.items()
        }

    def unbind(self, key: str) -> None:
        """Remove a value from the current context without affecting other tasks."""
        variable = self._context_vars.get(f"{self.FASTAPI_LOGGING_KIT_PREFIX}{key}")
        if variable is not None:
            variable.set(_UNSET)

    def reset(self, tokens: Dict[str, contextvars.Token]) -> None:
        """Restore values using tokens returned by :meth:`batch_bind`."""
        for key, token in reversed(tuple(tokens.items())):
            self._get_or_create(key).reset(token)

    def clear(self) -> None:
        """Clear package-owned values in the current context.

        Prefer :meth:`scoped_context` for request/task lifecycles because it restores
        outer values instead of discarding them.
        """
        with self._lock:
            variables = tuple(self._context_vars.values())
        for variable in variables:
            variable.set(_UNSET)

    def get_contextvars(self) -> Dict[str, Any]:
        """Return only currently bound values owned by this manager."""
        with self._lock:
            variables = tuple(self._context_vars.items())
        result: Dict[str, Any] = {}
        prefix_length = len(self.FASTAPI_LOGGING_KIT_PREFIX)
        for full_key, variable in variables:
            value = variable.get()
            if value is not _UNSET:
                result[full_key[prefix_length:]] = value
        return result

    @staticmethod
    def merge_contexts(
        bound_context: Dict[str, Any], local_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge contexts, with explicitly bound logger values taking priority."""
        merged = dict(local_context)
        merged.update(bound_context)
        return merged

    def get_merged_context(
        self, bound_logger_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Combine logger-bound values with current execution context."""
        return self.merge_contexts(bound_logger_context, self.get_contextvars())

    @contextmanager
    def scoped_context(self, **kwargs: Any) -> Generator[None, None, None]:
        """Temporarily bind values and always restore the previous context."""
        tokens = self.batch_bind(**kwargs)
        try:
            yield
        finally:
            self.reset(tokens)


manager: ContextVarManager = ContextVarManager()

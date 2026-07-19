import logging
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List

import pytest

from fast_logging.cache import cache
from fast_logging.middleware.monitor_log_size import (
    CACHE_KEY,
    MonitorLogSizeMiddleware,
)
from fast_logging.tests.constants import PYTHON_VERSION, PYTHON_VERSION_REASON

pytestmark = [
    pytest.mark.middleware,
    pytest.mark.monitor_log_size_middleware,
    pytest.mark.skipif(sys.version_info < PYTHON_VERSION, reason=PYTHON_VERSION_REASON),
]

LOGGER_NAME = "fast_logging.middleware.monitor_log_size"


async def _noop_app(scope: Any, receive: Any, send: Any) -> None:
    """A trivial ASGI application that does nothing."""


class TestShouldRunTask:
    """Test suite for the `should_run_task` scheduling check."""

    def test_returns_true_when_cache_is_empty(self) -> None:
        """Test that the audit is due when it has never run."""
        cache.delete(CACHE_KEY)

        assert MonitorLogSizeMiddleware.should_run_task() is True

    def test_returns_true_when_last_run_is_older_than_a_week(self) -> None:
        """Test that the audit is due once a week has passed."""
        cache.set(
            CACHE_KEY,
            datetime.now(timezone.utc) - timedelta(weeks=2),
            timeout=None,
        )

        assert MonitorLogSizeMiddleware.should_run_task() is True

    def test_returns_false_when_last_run_is_recent(self) -> None:
        """Test that a recent audit suppresses the next run."""
        cache.set(
            CACHE_KEY,
            datetime.now(timezone.utc) - timedelta(days=1),
            timeout=None,
        )

        assert MonitorLogSizeMiddleware.should_run_task() is False


class TestNow:
    """Test suite for the `_now` clock helper."""

    def test_returns_aware_utc_datetime(self) -> None:
        """Test that the helper returns a timezone-aware UTC datetime."""
        now = MonitorLogSizeMiddleware._now()

        assert isinstance(now, datetime)
        assert now.tzinfo is not None
        assert now.utcoffset() == timedelta(0)


class TestRunLogSizeCheck:
    """Test suite for the `run_log_size_check` command runner."""

    def test_runs_the_audit_command(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that the audit command is invoked and announced."""
        caplog.set_level(logging.INFO, logger=LOGGER_NAME)
        calls: List[bool] = []

        import fast_logging.commands.logs_size_audit as audit_module

        monkeypatch.setattr(
            audit_module, "run", lambda *args, **kwargs: calls.append(True)
        )

        MonitorLogSizeMiddleware(_noop_app).run_log_size_check()

        assert calls == [True]
        assert "Running 'logs_size_audit' command..." in caplog.text

    def test_logs_error_when_the_audit_raises(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that a failing audit is logged rather than propagated."""
        caplog.set_level(logging.INFO, logger=LOGGER_NAME)

        import fast_logging.commands.logs_size_audit as audit_module

        def failing_run(*args: Any, **kwargs: Any) -> None:
            """Raise as if the audit blew up."""
            raise RuntimeError("audit failed")

        monkeypatch.setattr(audit_module, "run", failing_run)

        MonitorLogSizeMiddleware(_noop_app).run_log_size_check()

        assert "Error running 'logs_size_audit' command: audit failed" in caplog.text


class TestMonitorLogSizeMiddlewareDispatch:
    """Test suite for the `MonitorLogSizeMiddleware.dispatch` flow."""

    async def test_runs_audit_and_stores_timestamp_when_due(
        self,
        scope_factory: Callable[..., Dict[str, Any]],
        asgi_caller: Callable[..., Any],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that a due audit runs and the run time is cached."""
        cache.delete(CACHE_KEY)
        calls: List[bool] = []

        import fast_logging.commands.logs_size_audit as audit_module

        monkeypatch.setattr(
            audit_module, "run", lambda *args, **kwargs: calls.append(True)
        )

        forwarded: List[Any] = []

        async def app(scope: Any, receive: Any, send: Any) -> None:
            """Record that the request was forwarded."""
            forwarded.append(scope)

        await asgi_caller(MonitorLogSizeMiddleware(app), scope_factory())

        assert calls == [True]
        assert forwarded
        assert isinstance(cache.get(CACHE_KEY), datetime)

    async def test_skips_audit_when_not_due(
        self,
        scope_factory: Callable[..., Dict[str, Any]],
        asgi_caller: Callable[..., Any],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that a recent audit is not repeated but the request runs."""
        last_run = datetime.now(timezone.utc) - timedelta(days=1)
        cache.set(CACHE_KEY, last_run, timeout=None)

        calls: List[bool] = []

        import fast_logging.commands.logs_size_audit as audit_module

        monkeypatch.setattr(
            audit_module, "run", lambda *args, **kwargs: calls.append(True)
        )

        forwarded: List[Any] = []

        async def app(scope: Any, receive: Any, send: Any) -> None:
            """Record that the request was forwarded."""
            forwarded.append(scope)

        await asgi_caller(MonitorLogSizeMiddleware(app), scope_factory())

        assert calls == []
        assert forwarded
        assert cache.get(CACHE_KEY) == last_run

    async def test_non_http_scope_skips_the_audit(
        self,
        scope_factory: Callable[..., Dict[str, Any]],
        asgi_caller: Callable[..., Any],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that non-HTTP traffic bypasses the audit entirely."""
        cache.delete(CACHE_KEY)
        calls: List[bool] = []

        import fast_logging.commands.logs_size_audit as audit_module

        monkeypatch.setattr(
            audit_module, "run", lambda *args, **kwargs: calls.append(True)
        )

        forwarded: List[Any] = []

        async def app(scope: Any, receive: Any, send: Any) -> None:
            """Record that the connection was forwarded."""
            forwarded.append(scope)

        await asgi_caller(
            MonitorLogSizeMiddleware(app), scope_factory(scope_type="websocket")
        )

        assert calls == []
        assert forwarded
        assert cache.get(CACHE_KEY) is None

"""Concurrency and nesting guarantees for request-scoped logging context."""

import asyncio

import pytest

from fastapi_logging_kit.contextvar.contextvar_manager import ContextVarManager


def test_nested_scope_restores_outer_values() -> None:
    manager = ContextVarManager()
    manager.bind(request_id="outer", tenant="acme")

    with manager.scoped_context(request_id="inner", trace_id="trace-1"):
        assert manager.get_contextvars() == {
            "request_id": "inner",
            "tenant": "acme",
            "trace_id": "trace-1",
        }

    assert manager.get_contextvars() == {
        "request_id": "outer",
        "tenant": "acme",
    }


def test_scope_restores_context_after_exception() -> None:
    manager = ContextVarManager()
    manager.bind(request_id="outer")

    with pytest.raises(RuntimeError):
        with manager.scoped_context(request_id="inner"):
            raise RuntimeError("failure")

    assert manager.get_contextvars() == {"request_id": "outer"}


@pytest.mark.asyncio
async def test_concurrent_tasks_do_not_share_request_context() -> None:
    manager = ContextVarManager()
    barrier = asyncio.Event()
    ready = 0

    async def worker(request_id: str) -> str:
        nonlocal ready
        with manager.scoped_context(request_id=request_id):
            ready += 1
            if ready == 2:
                barrier.set()
            await barrier.wait()
            await asyncio.sleep(0)
            return manager.get_contextvars()["request_id"]

    assert await asyncio.gather(worker("request-a"), worker("request-b")) == [
        "request-a",
        "request-b",
    ]

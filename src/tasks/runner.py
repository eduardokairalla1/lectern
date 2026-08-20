"""
Async execution helper for Celery tasks.

NOTE: Celery tasks are synchronous, but the whole service layer is async. Each
worker process keeps ONE persistent event loop and runs every task coroutine
on it, so the shared async clients (SQLAlchemy engine, Redis, LLMs) always see
the same loop. Using asyncio.run() per task would create/close a loop each
time, leaving pooled connections bound to a dead loop.

This relies on the worker's default prefork pool: each child process runs one
task at a time, so there is no concurrent access to _LOOP within a process. If
the worker pool is ever switched to threads/gevent, this must move to a
dedicated background-thread loop scheduled via asyncio.run_coroutine_threadsafe
instead, since multiple tasks could then share the same process concurrently.
"""

# --- IMPORTS ---
from collections.abc import Coroutine
from typing import Any

import asyncio


# --- GLOBALS ---
_LOOP: asyncio.AbstractEventLoop | None = None


# --- CODE ---
def run_async[T](coro: Coroutine[Any, Any, T]) -> T:
    """
    Runs a coroutine on the worker process' persistent event loop.

    :param coro: The coroutine to execute.

    :return: The coroutine's result.
    """
    # define the global loop variable
    global _LOOP

    # loop is not initialized or closed: create a new one
    if _LOOP is None or _LOOP.is_closed():
        _LOOP = asyncio.new_event_loop()
        asyncio.set_event_loop(_LOOP)

    # run the coroutine on the persistent loop
    return _LOOP.run_until_complete(coro)

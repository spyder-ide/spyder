# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

from __future__ import annotations
import asyncio
import atexit
import contextlib
from concurrent.futures import Future, CancelledError
import functools
import threading
import logging
import typing

_logger = logging.getLogger(__name__)


class AsyncDispatcher:
    """Decorator to convert a coroutine to a sync function.

    Helper class to facilitate the conversion of coroutines to sync functions
    or to run a coroutine as a sync function without the need to call the event
    loop method.

    Usage
    ------
    As a decorator:
    ```
    @AsyncDispatcher.dispatch()
    async def my_coroutine():
        pass

    my_coroutine()
    ```

    As a class wrapper:
    ```
    sync_coroutine = AsyncDispatcher(my_coroutine)

    sync_coroutine()
    ```
    """

    __closed = False
    __running_loops: typing.ClassVar[dict[int, asyncio.AbstractEventLoop]] = {}
    __running_threads: typing.ClassVar[dict[int, threading.Thread]] = {}
    _running_tasks: typing.ClassVar[list[Future]] = []

    def __init__(self, coro, *, loop=None, early_return=True):
        """Initialize the decorator.

        Parameters
        ----------
        coro : coroutine
            The coroutine to be wrapped.
        loop : asyncio.AbstractEventLoop, optional
            The event loop to be used, by default get the current event loop.
        """
        if not asyncio.iscoroutinefunction(coro):
            msg = f"{coro} is not a coroutine function"
            raise TypeError(msg)
        self._coro = coro
        self._loop = self._ensure_running_loop(loop)
        self._early_return = early_return

    def __call__(self, *args, **kwargs):
        task = asyncio.run_coroutine_threadsafe(
            self._coro(*args, **kwargs), loop=self._loop
        )
        if self._early_return:
            AsyncDispatcher._running_tasks.append(task)
            task.add_done_callback(self._callback_task_done)
            return task
        return task.result()

    @classmethod
    def dispatch(cls, *, loop=None, early_return=True):
        """Create a decorator to run the coroutine with a given event loop."""

        def decorator(coro):
            @functools.wraps(coro)
            def wrapper(*args, **kwargs):
                return cls(coro, loop=loop, early_return=early_return)(
                    *args, **kwargs
                )

            return wrapper

        return decorator

    def _callback_task_done(self, future):
        AsyncDispatcher._running_tasks.remove(future)
        with contextlib.suppress(asyncio.CancelledError, CancelledError):
            if (exception := future.exception()) is not None:
                raise exception

    @classmethod
    def _ensure_running_loop(cls, loop=None):
        if loop is None:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
            finally:
                loop_id = hash(loop)
        elif not isinstance(loop, asyncio.AbstractEventLoop):
            loop_id = loop
            loop = cls.__running_loops.get(loop_id, asyncio.new_event_loop())
        else:
            loop_id = hash(loop)

        try:
            if loop.is_running():
                return loop
        except RuntimeError:
            _logger.exception(
                "Failed to check if the loop is running, defaulting to the "
                "current loop."
            )
            return asyncio.get_event_loop()

        return cls.__run_loop(loop_id, loop)

    @classmethod
    def __run_loop(cls, loop_id, loop):
        cls.__running_threads[loop_id] = threading.Thread(
            target=loop.run_forever, daemon=True
        )
        cls.__running_threads[loop_id].start()
        cls.__running_loops[loop_id] = loop
        return loop

    @staticmethod
    @atexit.register
    def close():
        """Close the thread pool."""
        if AsyncDispatcher.__closed:
            return
        AsyncDispatcher.cancel_all()
        AsyncDispatcher.join()
        AsyncDispatcher.__closed = True

    @classmethod
    def cancel_all(cls):
        """Cancel all running tasks."""
        for task in cls._running_tasks:
            task.cancel()

    @classmethod
    def join(cls, timeout: float | None = None):
        """Close all running loops and join the threads."""
        for loop_id in list(cls.__running_loops.keys()):
            cls._stop_running_loop(loop_id, timeout)

    @classmethod
    def _stop_running_loop(cls, loop_id, timeout=None):
        thread = cls.__running_threads.pop(loop_id, None)
        loop = cls.__running_loops.pop(loop_id, None)

        if loop is None:
            return

        if thread is None:
            return

        if loop.is_closed():
            thread.join(timeout)
            return

        loop_stoped = threading.Event()

        def _stop():
            loop.stop()
            loop_stoped.set()

        loop.call_soon_threadsafe(_stop)

        loop_stoped.wait(timeout)
        thread.join(timeout)
        loop.close()

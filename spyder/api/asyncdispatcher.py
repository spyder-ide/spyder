# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

from __future__ import annotations
import asyncio
import atexit
from concurrent.futures import CancelledError, Future
import contextlib
import functools
import logging
import sys
import threading
import typing


if sys.version_info < (3, 10):
    from typing_extensions import ParamSpec
else:
    from typing import ParamSpec  # noqa: ICN003

_logger = logging.getLogger(__name__)


LoopID = typing.Union[typing.Hashable, asyncio.AbstractEventLoop]

P = ParamSpec("P")

T = typing.TypeVar("T")


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

    __rlock = threading.RLock()

    __closed = False
    __running_threads: typing.ClassVar[dict[typing.Hashable, _LoopRunner]] = {}
    _running_tasks: typing.ClassVar[list[Future]] = []

    def __init__(self,
                 async_func: typing.Callable[..., typing.Coroutine[
                             typing.Any, typing.Any, typing.Any]],
                 *,
                 loop: LoopID | None = None,
                 early_return: bool = True):
        """Initialize the decorator.

        Parameters
        ----------
        coro : coroutine
            The coroutine to be wrapped.
        loop : asyncio.AbstractEventLoop, optional
            The event loop to be used, by default get the current event loop.
        """
        if not asyncio.iscoroutinefunction(async_func):
            msg = f"{async_func} is not a coroutine function"
            raise TypeError(msg)
        self._async_func = async_func
        self._loop = self._ensure_running_loop(loop)
        self._early_return = early_return

    def __call__(self, *args, **kwargs):
        task = asyncio.run_coroutine_threadsafe(
            self._async_func(*args, **kwargs), loop=self._loop
        )
        if self._early_return:
            AsyncDispatcher._running_tasks.append(task)
            task.add_done_callback(self._callback_task_done)
            return task
        return task.result()

    @classmethod
    def dispatch(cls,
                 *,
                 loop: LoopID | None = None,
                 early_return: bool = True):
        """Create a decorator to run the coroutine with a given event loop."""

        def decorator(
            async_func: typing.Callable[P, typing.Coroutine[typing.Any,
                                                            typing.Any, T]]
        ) -> typing.Callable[P, Future[T] | T]:
            @functools.wraps(async_func)
            def wrapper(*args, **kwargs):
                return cls(async_func, loop=loop, early_return=early_return)(
                    *args, **kwargs
                )

            return wrapper

        return decorator

    def _callback_task_done(self, future: Future):
        AsyncDispatcher._running_tasks.remove(future)
        with contextlib.suppress(asyncio.CancelledError, CancelledError):
            if (exception := future.exception()) is not None:
                raise exception

    @classmethod
    def _ensure_running_loop(
        cls,
        loop_id: LoopID | None = None
    ) -> asyncio.AbstractEventLoop:
        loop, loop_id = cls.get_event_loop(loop_id)

        try:
            if loop.is_running():
                return loop
        except RuntimeError:
            _logger.exception(
                "Failed to check if the loop is running, defaulting to the "
                "current loop."
            )
            return asyncio.get_event_loop()

        with cls.__rlock:
            # Re-check, perhaps it was created in the meantime...
            if loop_id not in cls.__running_threads:
                cls.__run_loop(loop_id, loop)
                if loop_id is None:
                    asyncio.set_event_loop(loop)

        return loop

    @classmethod
    def get_event_loop(
        cls, loop_id: LoopID | None = None
    ) -> tuple[asyncio.AbstractEventLoop, typing.Hashable | None]:
        if loop_id is None:
            try:
                return asyncio.get_running_loop(), None
            except RuntimeError:  # noqa: S110
                pass
        elif isinstance(loop_id, asyncio.AbstractEventLoop):
            return loop_id, hash(loop_id)

        running_thread = cls.__running_threads.get(loop_id)
        if running_thread is not None:
            return running_thread.loop, loop_id

        return asyncio.new_event_loop(), loop_id

    @classmethod
    def __run_loop(cls,
                   loop_id: typing.Hashable,
                   loop: asyncio.AbstractEventLoop):
        if loop_id not in cls.__running_threads:
            with cls.__rlock:
                if loop_id not in cls.__running_threads:
                    cls.__running_threads[loop_id] = \
                        _LoopRunner(loop_id, loop)
                    cls.__running_threads[loop_id].start()

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
        for loop_id in list(cls.__running_threads.keys()):
            cls._stop_running_loop(loop_id, timeout)

    @classmethod
    def _stop_running_loop(cls,
                           loop_id: LoopID,
                           timeout: int | None = None):
        runner = cls.__running_threads.pop(loop_id, None)

        if runner is None:
            return

        runner.join(timeout)


class _LoopRunner(threading.Thread):
    """A task runner that runs an asyncio event loop on a background thread."""

    def __init__(self, loop_id: str,
                 loop: asyncio.AbstractEventLoop):
        super().__init__(daemon=True, name=f"AsyncDispatcher-{loop_id}")
        self.__loop = loop
        self.__loop_stopped = threading.Event()

    @property
    def loop(self):
        return self.__loop

    def run(self):
        asyncio.set_event_loop(self.__loop)
        try:
            self.__loop.run_forever()
        finally:
            self.__loop.close()
            self.__loop_stopped.set()

    def stop(self):
        self.__loop.call_soon_threadsafe(self.__loop.stop)

    def join(self, timeout: float | None = None):
        if not self.__loop_stopped.is_set():
            self.stop()
            self.__loop_stopped.wait(timeout)
        super().join(timeout)


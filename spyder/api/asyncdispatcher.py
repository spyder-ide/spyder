# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

from __future__ import annotations
import asyncio
import asyncio.events
from asyncio.tasks import _current_tasks  # type: ignore
import atexit
from concurrent.futures import CancelledError, Future
import contextlib
from contextlib import contextmanager
import functools
from heapq import heappop
import logging
import os
import sys
import threading
import typing


if sys.version_info < (3, 10):
    from typing_extensions import ParamSpec
else:
    from typing import ParamSpec  # noqa: ICN003

_logger = logging.getLogger(__name__)


LoopID = typing.Union[typing.Hashable, asyncio.AbstractEventLoop]


_P = ParamSpec("_P")
_T = typing.TypeVar("_T")
_RT = typing.TypeVar("_RT")


class AsyncDispatcher(typing.Generic[_RT]):
    """Decorator to run a coroutine in a specific event loop."""

    __rlock = threading.RLock()

    __closed = False
    __running_threads: typing.ClassVar[dict[typing.Hashable, _LoopRunner]] = {}
    _running_tasks: typing.ClassVar[list[Future]] = []

    @typing.overload
    def __init__(
        self: AsyncDispatcher[Future[_T]],
        *,
        loop: LoopID | None = ...,
        early_return: typing.Literal[True] = ...,
        return_awaitable: typing.Literal[False] = ...
    ):
        ...

    @typing.overload
    def __init__(
        self: AsyncDispatcher[typing.Awaitable[_T]],
        *,
        loop: LoopID | None = ...,
        early_return: typing.Literal[True] = ...,
        return_awaitable: typing.Literal[True] = ...
    ):
        ...

    @typing.overload
    def __init__(
        self: AsyncDispatcher[_T],
        *,
        loop: LoopID | None = ...,
        early_return: typing.Literal[False] = ...,
        return_awaitable: typing.Literal[False] = ...
    ):
        ...

    @typing.overload
    def __init__(
        self: AsyncDispatcher[typing.Awaitable[_T]],
        *,
        loop: LoopID | None = ...,
        early_return: typing.Literal[False] = ...,
        return_awaitable: typing.Literal[True] = ...
    ):
        ...

    def __init__(self,
                 *,
                 loop: LoopID | None = None,
                 early_return: bool = True,
                 return_awaitable: bool = False):
        """
        Decorate a coroutine to run in a specific event loop.

        The `loop` parameter can be an existing loop or a hashable to identify
        an existing/new one (to be) created by the AsyncDispatcher. If the
        loop is not running, it will be started in a new thread and managed by
        the AsyncDispatcher.

        This instance can be called with the same arguments as the coroutine it
        wraps and will return a concurrent Future object, or an awaitable
        Future for the current running event loop or the result of the coroutine
        depending on the `early_return` and `return_awaitable` parameters.

        Usage
        -----
        Non-Blocking usage (returns a concurrent Future):
        ```
        @AsyncDispatcher()
        async def my_coroutine(...):
            ...

        future = my_coroutine(...)  # Non-blocking call

        result = future.result()  # Blocking call
        ```

        Blocking usage (returns the result):
        ```
        @AsyncDispatcher(early_return=False)
        async def my_coroutine(...):
            ...

        result = my_coroutine(...)  # Blocking call
        ```

        Coroutine usage (returns an awaitable Future):
        ```
        @AsyncDispatcher(return_awaitable=True)
        async def my_coroutine(...):
            ...

        result = await my_coroutine(...)  # Wait for the result to be ready
        ```

        Parameters
        ----------
        loop : LoopID, optional (default: None)
            The event loop to be used, by default get the current event loop.
        early_return : bool, optional (default: True)
            Return the coroutine as a concurrent Future before it is done.
        return_awaitable : bool, optional (default: False)
            Return the coroutine as an awaitable (asyncio) Future instead
            of a concurrent Future. Idenpendently of the value of `early_return`.
        """
        self._loop = self._ensure_running_loop(loop)
        self._early_return = early_return
        self._return_awaitable = return_awaitable
    
    @typing.overload
    def __call__(
        self: AsyncDispatcher[typing.Awaitable[_T]],
        async_func: typing.Callable[_P, typing.Awaitable[_T]],
    ) -> typing.Callable[_P, typing.Awaitable[_T]]:
        ...

    @typing.overload
    def __call__(
        self: AsyncDispatcher[Future[_T]],
        async_func: typing.Callable[_P, typing.Awaitable[_T]],
    ) -> typing.Callable[_P, Future[_T]]:
        ...

    @typing.overload
    def __call__(
        self: AsyncDispatcher[_T],
        async_func: typing.Callable[_P, typing.Awaitable[_T]],
    ) -> typing.Callable[_P, _T]:
        ...

    def __call__(
            self,
            async_func: typing.Callable[_P, typing.Awaitable[_T]],
        ) -> typing.Callable[_P, typing.Union[_T, Future[_T], typing.Awaitable[_T]]]:
        """
        Run the coroutine in the event loop.

        Parameters
        ----------
        *args : tuple
            The positional arguments to be passed to the coroutine.
        **kwargs : dict
            The keyword arguments to be passed to the coroutine.

        Returns
        -------
        concurrent.Future or asyncio.Future or result of the coroutine

        Raises
        ------
        TypeError
            If the function is not a coroutine function.
        """
        if not asyncio.iscoroutinefunction(async_func):
            msg = f"{async_func} is not a coroutine function"
            raise TypeError(msg)

        @functools.wraps(async_func)
        def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> typing.Union[_T, Future[_T], typing.Awaitable[_T]]:
            task = asyncio.run_coroutine_threadsafe(
                async_func(*args, **kwargs), loop=self._loop
            )
            if self._return_awaitable:
                return asyncio.wrap_future(task, loop=asyncio.get_running_loop())

            if self._early_return:
                AsyncDispatcher._running_tasks.append(task)
                task.add_done_callback(self._callback_task_done)
                return task
            return task.result()

        return wrapper

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
                    _patch_loop_as_reentrant(loop)  # ipykernel compatibility
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
                           timeout: float | None = None):
        runner = cls.__running_threads.pop(loop_id, None)

        if runner is None:
            return

        runner.join(timeout)


class _LoopRunner(threading.Thread):
    """A task runner that runs an asyncio event loop on a background thread."""

    def __init__(self, loop_id: typing.Hashable,
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


def _patch_loop_as_reentrant(loop):
    """Patch an event loop in order to make it reentrant.

    This is a simplified version of the 'nest_asyncio'.
    """

    if hasattr(loop, '_nest_patched'):
        """Use same check as asyncio to avoid re-patching."""
        return

    def run_forever(self):
        with manage_run(self), manage_asyncgens(self):
            while True:
                self._run_once()
                if self._stopping:
                    break
        self._stopping = False

    def run_until_complete(self, future):
        with manage_run(self):
            f = asyncio.ensure_future(future, loop=self)
            if f is not future:
                f._log_destroy_pending = False
            while not f.done():
                self._run_once()
                if self._stopping:
                    break
            if not f.done():
                raise RuntimeError(
                    'Event loop stopped before Future completed.')
            return f.result()

    def _run_once(self):
        """
        Simplified re-implementation of asyncio's _run_once that
        runs handles as they become ready.
        """
        ready = self._ready
        scheduled = self._scheduled
        while scheduled and scheduled[0]._cancelled:
            heappop(scheduled)

        timeout = (
            0 if ready or self._stopping
            else min(max(
                scheduled[0]._when - self.time(), 0), 86400) if scheduled
            else None)
        event_list = self._selector.select(timeout)
        self._process_events(event_list)

        end_time = self.time() + self._clock_resolution
        while scheduled and scheduled[0]._when < end_time:
            handle = heappop(scheduled)
            ready.append(handle)

        for _ in range(len(ready)):
            if not ready:
                break
            handle = ready.popleft()
            if not handle._cancelled:
                # preempt the current task so that that checks in
                # Task.__step do not raise
                curr_task = _current_tasks.pop(self, None)

                try:
                    handle._run()
                finally:
                    # restore the current task
                    if curr_task is not None:
                        _current_tasks[self] = curr_task

        handle = None

    @contextmanager
    def manage_run(self):
        """Set up the loop for running."""
        self._check_closed()
        old_thread_id = self._thread_id
        old_running_loop = asyncio.events._get_running_loop()
        try:
            self._thread_id = threading.get_ident()
            asyncio.events._set_running_loop(self)
            self._num_runs_pending += 1
            if self._is_proactorloop:
                if self._self_reading_future is None:
                    self.call_soon(self._loop_self_reading)
            yield
        finally:
            self._thread_id = old_thread_id
            asyncio.events._set_running_loop(old_running_loop)
            self._num_runs_pending -= 1
            if self._is_proactorloop:
                if (self._num_runs_pending == 0
                        and self._self_reading_future is not None):
                    ov = self._self_reading_future._ov
                    self._self_reading_future.cancel()
                    if ov is not None:
                        self._proactor._unregister(ov)
                    self._self_reading_future = None

    @contextmanager
    def manage_asyncgens(self):
        if not hasattr(sys, 'get_asyncgen_hooks'):
            # Python version is too old.
            return
        old_agen_hooks = sys.get_asyncgen_hooks()
        try:
            self._set_coroutine_origin_tracking(self._debug)
            if self._asyncgens is not None:
                sys.set_asyncgen_hooks(
                    firstiter=self._asyncgen_firstiter_hook,
                    finalizer=self._asyncgen_finalizer_hook)
            yield
        finally:
            self._set_coroutine_origin_tracking(False)
            if self._asyncgens is not None:
                sys.set_asyncgen_hooks(*old_agen_hooks)

    def _check_running(self):
        """Do not throw exception if loop is already running."""
        pass

    if not isinstance(loop, asyncio.BaseEventLoop):
        raise ValueError('Can\'t patch loop of type %s' % type(loop))
    cls = loop.__class__
    setattr(cls, 'run_forever', run_forever)
    setattr(cls, 'run_until_complete', run_until_complete)
    setattr(cls, '_run_once', _run_once)
    setattr(cls, '_check_running', _check_running)
    setattr(cls, '_num_runs_pending', 1 if loop.is_running() else 0)
    setattr(cls, '_is_proactorloop', (
        os.name == 'nt' and issubclass(cls, asyncio.ProactorEventLoop)))
    setattr(cls, '_nest_patched', True)

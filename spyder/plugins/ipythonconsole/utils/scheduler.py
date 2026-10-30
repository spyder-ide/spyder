# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Run code from outside callers (e.g. AI agents) in a console one at a time,
without getting in the way of the user.

Code from outside callers waits while the console is busy, so callers can
share a console without failing or mixing their runs. The user goes first:
their runs (typed at the prompt or started from Spyder, e.g. with F5) never
wait for outside code that hasn't started yet, and outside code doesn't
start while the user is typing at the prompt.

The scheduler also remembers who started the code that is running, so only
that caller can interrupt it, or send commands to the debugger if the code
stopped in it.
"""

# Standard library imports
from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import Future
from dataclasses import dataclass, field
import time
from typing import TYPE_CHECKING

# Third-party imports
from qtpy.QtCore import QEvent, QObject, QTimer

# Local imports
from spyder.api.plugins import Caller, ExposedCallError

if TYPE_CHECKING:
    from spyder.plugins.ipythonconsole.widgets import ShellWidget

# Outside code doesn't start while the user has text at the prompt that they
# typed less than this many seconds ago.
USER_TYPING_GRACE = 3

# How often to check if waiting code can start, in milliseconds.
POLL_INTERVAL = 250

# Waits shorter than this aren't reported to callers, in seconds.
REPORTED_WAIT = 1


@dataclass(eq=False)
class _Run:
    caller: Caller | None
    start: Callable[[float], Future]
    deadline: float
    future: Future = field(default_factory=Future)
    submitted: float = field(default_factory=time.monotonic)


def describe_caller(caller: Caller | None) -> str:
    """Name of a caller for messages, e.g. ``Agent 2``."""
    if caller is None:
        return "another agent"
    return caller.name


class ConsoleScheduler(QObject):
    """Run code from outside callers in a console one at a time."""

    def __init__(self, shellwidget: ShellWidget) -> None:
        super().__init__(shellwidget)
        self.shellwidget = shellwidget
        self._queue: list[_Run] = []

        # Whether code from an outside caller is running, and who started it.
        # It's running until the console shows the IPython prompt again, even
        # if the caller stopped waiting for it or it stopped in the debugger.
        self._running = False
        self._running_caller: Caller | None = None

        self._last_key_press = 0.0
        shellwidget._control.installEventFilter(self)
        shellwidget.sig_prompt_ready.connect(self._on_prompt_ready)
        shellwidget.sig_shellwidget_deleted.connect(
            lambda _shellwidget: self.cancel_all("the console was closed.")
        )

        self._timer = QTimer(self)
        self._timer.setInterval(POLL_INTERVAL)
        self._timer.timeout.connect(self._process)

    # ---- Public API
    def submit(
        self,
        caller: Caller | None,
        start: Callable[[float], Future],
        timeout: float,
    ) -> Future:
        """
        Run code for ``caller`` when the console is free.

        Parameters
        ----------
        caller : Caller or None
            Who is running the code.
        start : Callable
            Function that starts running the code and returns a future with
            its result. It takes the seconds left of ``timeout``.
        timeout : float
            Seconds to wait for the code to start and finish. If the console
            is still busy when they pass, the code doesn't run.

        Returns
        -------
        Future
            Resolved like the future returned by ``start``. If the code had
            to wait, its result (a dict) gets a note about it.
        """
        run = _Run(caller, start, time.monotonic() + timeout)
        self._queue.append(run)
        self._process()
        if self._queue:
            self._timer.start()
        return run.future

    def cancel(self, caller: Caller | None) -> int:
        """
        Cancel the code of ``caller`` that is waiting to run.

        Returns
        -------
        int
            Number of runs cancelled.
        """
        cancelled = [run for run in self._queue if run.caller == caller]
        for run in cancelled:
            self._queue.remove(run)
            run.future.set_exception(
                ExposedCallError(
                    "The code didn't run: it was cancelled with "
                    "interrupt_console while waiting for the console."
                )
            )
        return len(cancelled)

    def cancel_all(self, reason: str) -> None:
        """Cancel all the code waiting to run, e.g. if the console closes."""
        self._timer.stop()
        queue, self._queue = self._queue, []
        for run in queue:
            if not run.future.done():
                run.future.set_exception(
                    ExposedCallError(f"The code didn't run: {reason}")
                )

    def is_running_outside_code(self) -> bool:
        """Whether the code running was started by an outside caller."""
        return self._running

    def get_running_caller(self) -> Caller | None:
        """
        Outside caller that started the code that is running, if any. Check
        :meth:`is_running_outside_code` to tell the user's code apart from
        code of callers without identity.
        """
        return self._running_caller

    def get_waiting(self) -> int:
        """Number of runs waiting for the console."""
        return len(self._queue)

    def describe_activity(self) -> str | None:
        """What keeps the console busy, for messages to callers."""
        shellwidget = self.shellwidget
        if not shellwidget.spyder_kernel_ready:
            return "its kernel is starting"
        if self._running:
            who = describe_caller(self._running_caller)
            if shellwidget.is_debugging():
                return f"{who} is debugging in it"
            return f"{who} is running code in it"
        if shellwidget.is_debugging():
            return "the user is debugging in it"
        if shellwidget._executing or shellwidget._execute_queue:
            return "the user is running code in it"
        if self._is_user_typing():
            return "the user is typing in it"
        return None

    # ---- Qt methods
    def eventFilter(self, obj, event) -> bool:
        if event.type() == QEvent.KeyPress:
            self._last_key_press = time.monotonic()
        return False

    # ---- Private API
    def _is_user_typing(self) -> bool:
        shellwidget = self.shellwidget
        if time.monotonic() - self._last_key_press >= USER_TYPING_GRACE:
            return False
        return bool(shellwidget._get_input_buffer(force=True).strip())

    def _can_start(self) -> bool:
        return not self._running and self.describe_activity() is None

    def _on_prompt_ready(self) -> None:
        # The console is back at the IPython prompt, so the code finished
        # (or the kernel restarted)
        if not self.shellwidget._executing:
            self._running = False
            self._running_caller = None

        # Let Spyder start the user's runs that are waiting first
        QTimer.singleShot(0, self._process)

    def _process(self) -> None:
        now = time.monotonic()
        for run in [run for run in self._queue if now >= run.deadline]:
            self._queue.remove(run)
            run.future.set_exception(
                ExposedCallError(
                    f"The code didn't run: the console was still busy "
                    f"({self.describe_activity() or 'it was busy'}). Try "
                    f"again later, or use another console (see list_consoles "
                    f"and new_console)."
                )
            )

        if self._queue and self._can_start():
            self._start(self._queue.pop(0))

        if not self._queue:
            self._timer.stop()

    def _start(self, run: _Run) -> None:
        now = time.monotonic()
        waited = now - run.submitted

        self._running = True
        self._running_caller = run.caller
        try:
            future = run.start(max(run.deadline - now, 1))
        except Exception as error:
            self._running = False
            self._running_caller = None
            run.future.set_exception(error)
            QTimer.singleShot(0, self._process)
            return

        def on_done(future):
            try:
                result = future.result()
            except Exception as error:
                run.future.set_exception(error)
                return
            if waited >= REPORTED_WAIT and isinstance(result, dict):
                result.setdefault("notes", []).insert(
                    0,
                    f"The code waited {waited:.0f} seconds for the console "
                    f"to be free before running.",
                )
            run.future.set_result(result)

        future.add_done_callback(on_done)


def get_scheduler(shellwidget: ShellWidget) -> ConsoleScheduler:
    """Get the scheduler of a console, creating it if needed."""
    scheduler = getattr(shellwidget, "_console_scheduler", None)
    if scheduler is None:
        scheduler = ConsoleScheduler(shellwidget)
        shellwidget._console_scheduler = scheduler
    return scheduler

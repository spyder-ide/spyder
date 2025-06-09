from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Callable, ContextManager

from rope.base.taskhandle import BaseJobSet, BaseTaskHandle

from pylsp._utils import throttle
from pylsp.workspace import Workspace

log = logging.getLogger(__name__)
Report = Callable[[str, int], None]


class PylspJobSet(BaseJobSet):
    count: int = 0
    done: int = 0
    _reporter: Report
    _report_iter: ContextManager
    job_name: str = ""

    def __init__(self, count: int | None, report_iter: ContextManager) -> None:
        if count is not None:
            self.count = count
        self._reporter = report_iter.__enter__()
        self._report_iter = report_iter

    def started_job(self, name: str | None) -> None:
        if name:
            self.job_name = name

    def finished_job(self) -> None:
        self.done += 1
        if self.get_percent_done() is not None and int(self.get_percent_done()) >= 100:
            if self._report_iter is None:
                return
            self._report_iter.__exit__(None, None, None)
            self._report_iter = None
        else:
            self._report()

    def check_status(self) -> None:
        pass

    def get_percent_done(self) -> float | None:
        if self.count == 0:
            return 0
        return (self.done / self.count) * 100

    def increment(self) -> None:
        """
        Increment the number of tasks to complete.

        This is used if the number is not known ahead of time.
        """
        self.count += 1
        self._report()

    @throttle(0.5)
    def _report(self) -> None:
        percent = int(self.get_percent_done())
        message = f"{self.job_name} {self.done}/{self.count}"
        log.debug(f"Reporting {message} {percent}%")
        self._reporter(message, percent)


class PylspTaskHandle(BaseTaskHandle):
    name: str
    observers: list
    job_sets: list[PylspJobSet]
    stopped: bool
    workspace: Workspace
    _report: Callable[[str, str], None]

    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace
        self.job_sets = []
        self.observers = []

    def create_jobset(self, name="JobSet", count: int | None = None):
        report_iter = self.workspace.report_progress(
            name, None, None, skip_token_initialization=True
        )
        result = PylspJobSet(count, report_iter)
        self.job_sets.append(result)
        self._inform_observers()
        return result

    def stop(self) -> None:
        pass

    def current_jobset(self) -> BaseJobSet | None:
        pass

    def add_observer(self) -> None:
        pass

    def is_stopped(self) -> bool:
        pass

    def get_jobsets(self) -> Sequence[BaseJobSet]:
        pass

    def _inform_observers(self) -> None:
        for observer in self.observers:
            observer()

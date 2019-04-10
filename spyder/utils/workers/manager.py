# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------
"""
Manager and workers for running long processes in non (GUI) blocking threads.
"""

# Standard library imports
from collections import deque
import logging
import sys

# Third party imports
from qtpy.QtCore import QObject, QThread, QTimer, Signal

# Local imports
from spyder.utils.workers import ProcessWorker, PythonWorker


logger = logging.getLogger(__name__)


class WorkerManager(QObject):
    """Spyder Worker Manager for Generic Workers."""
    sig_manager_shutdown = Signal(list)
    sig_manager_empty = Signal()

    _WORKER_MANAGERS = []

    def __init__(self, max_threads=10):
        """Spyder Worker Manager for Generic Workers."""
        super(QObject, self).__init__()
        self._queue_workers = deque()
        self._threads = []
        self._workers = []
        self._timer = QTimer()
        self._timer_worker_delete = QTimer()
        self._running_threads = 0
        self._max_threads = max_threads

        # Keeps references to workers. Needed to avoid C/C++ object errors
        self._bag_collector = deque()

        self._timer.setInterval(333)
        self._timer.timeout.connect(self._start)
        self._timer_worker_delete.setInterval(500)
        self._timer_worker_delete.timeout.connect(self._clean_workers)

        WorkerManager._WORKER_MANAGERS.append(self)

    def _start(self, worker=None):
        """Start threads and check for inactive workers."""
        if worker:
            self._queue_workers.append(worker)

        if self._queue_workers and self._running_threads < self._max_threads:
            logger.info(
                'Queue: {0} Running: {1} Workers: {2} Threads: {3}'.format(
                    len(self._queue_workers),
                    self._running_threads,
                    len(self._workers),
                    len(self._threads),
                )
            )
            self._running_threads += 1

            thread = QThread()
            worker = self._queue_workers.popleft()
            if isinstance(worker, PythonWorker):
                worker.moveToThread(thread)

            worker.sig_finished.connect(thread.quit)
            thread.started.connect(worker._start)
            thread.start()

            self._threads.append(thread)

        else:
            self._timer.start()

        self._close_workers()
        self._close_threads()

        if len(self._threads) == 0 and len(self._workers) == 0:
            self._timer.stop()
            self._timer_worker_delete.start()
            self.sig_manager_empty.emit()

    def _close_workers(self, force=False):
        """Attempt to close any finished workers."""
        for w in self._workers:
            if force or w.is_finished():
                w.deleteLater()
                self._bag_collector.append(w)
                self._workers.remove(w)

    def _close_threads(self, force=False):
        """Attempt to close any finished threads."""
        for t in self._threads:
            if force or t.isFinished():
                t.quit()
                t.deleteLater()
                self._threads.remove(t)
                self._running_threads -= 1
                del t

    def _clean_workers(self):
        """Delete periodically workers in workers bag."""
        while self._bag_collector:
            w = self._bag_collector.popleft()
            del w
        self._timer_worker_delete.stop()

    def _create_worker(self, worker):
        """Common worker setup."""
        worker.sig_started.connect(self._start)
        self._workers.append(worker)

    # --- API
    # ------------------------------------------------------------------------
    def create_python_worker(self, func, *args, **kwargs):
        """Create a new python worker instance."""
        worker = PythonWorker(func, args, kwargs)
        self._create_worker(worker)
        return worker

    def create_process_worker(self, cmd_list, environ=None):
        """Create a new process worker instance."""
        worker = ProcessWorker(cmd_list, environ=environ)
        self._create_worker(worker)
        return worker

    def terminate_all(self):
        """Terminate all worker processes."""
        for worker in self._workers:
            worker.terminate()
        self._queue_workers = deque()

    def shutdown(self):
        """Shutdown manager instance."""
        logger.info('Shutting down worker manager {}'.format(self))
        self._close_workers(force=True)
        self._close_threads(force=True)
        self._clean_workers()
        self._timer.stop()
        self._timer_worker_delete.stop()
        WorkerManager._WORKER_MANAGERS.remove(self)
        self.sig_manager_shutdown.emit(WorkerManager._WORKER_MANAGERS)

    @classmethod
    def shutdown_managers(cls):
        """Shutdown manager instances."""
        for manager in cls._WORKER_MANAGERS:
            manager.shutdown()

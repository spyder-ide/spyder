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
import sys

# Third party imports
from qtpy.QtCore import QObject, QThread, QTimer

# Local imports
from spyder.utils.workers import ProcessWorker, PythonWorker


class WorkerManager(QObject):
    """Spyder Worker Manager for Generic Workers."""

    def __init__(self, max_threads=10):
        """Spyder Worker Manager for Generic Workers."""
        super(QObject, self).__init__()
        self._queue = deque()
        self._queue_workers = deque()
        self._threads = []
        self._workers = []
        self._timer = QTimer()
        self._timer_worker_delete = QTimer()
        self._running_threads = 0
        self._max_threads = max_threads

        # Keeps references to old workers
        # Needed to avoid C++/python object errors
        self._bag_collector = deque()

        self._timer.setInterval(333)
        self._timer.timeout.connect(self._start)
        self._timer_worker_delete.setInterval(5000)
        self._timer_worker_delete.timeout.connect(self._clean_workers)

    def _clean_workers(self):
        """Delete periodically workers in workers bag."""
        while self._bag_collector:
            self._bag_collector.popleft()
        self._timer_worker_delete.stop()

    def _start(self, worker=None):
        """Start threads and check for inactive workers."""
        if worker:
            self._queue_workers.append(worker)

        if self._queue_workers and self._running_threads < self._max_threads:
            # print('Queue: {0} Running: {1} Workers: {2} '
            #        'Threads: {3}'.format(len(self._queue_workers),
            #                                  self._running_threads,
            #                                  len(self._workers),
            #                                  len(self._threads)))
            self._running_threads += 1
            worker = self._queue_workers.popleft()
            thread = QThread()
            if isinstance(worker, PythonWorker):
                worker.moveToThread(thread)
                worker.sig_finished.connect(thread.quit)
                thread.started.connect(worker._start)
                thread.start()
            elif isinstance(worker, ProcessWorker):
                thread.quit()
                worker._start()
            self._threads.append(thread)
        else:
            self._timer.start()

        if self._workers:
            for w in self._workers:
                if w.is_finished():
                    self._bag_collector.append(w)
                    self._workers.remove(w)

        if self._threads:
            for t in self._threads:
                if t.isFinished():
                    self._threads.remove(t)
                    self._running_threads -= 1

        if len(self._threads) == 0 and len(self._workers) == 0:
            self._timer.stop()
            self._timer_worker_delete.start()

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

        # for thread in self._threads:
        #     try:
        #         thread.terminate()
        #         thread.wait()
        #     except Exception:
        #         pass
        self._queue_workers = deque()

    def _create_worker(self, worker):
        """Common worker setup."""
        worker.sig_started.connect(self._start)
        self._workers.append(worker)


# --- Local testing
# -----------------------------------------------------------------------------
def ready_print(worker, output, error):  # pragma: no cover
    """Print worker output for tests."""
    print(worker, output, error)  # spyder: test-skip


def sleeping_func(arg, secs=10, result_queue=None):
    """This methods illustrates how the workers can be used."""
    import time
    time.sleep(secs)
    if result_queue is not None:
        result_queue.put(arg)
    else:
        return arg


def local_test():  # pragma: no cover
    """Main local test."""
    from spyder.utils.qthelpers import qapplication
    app = qapplication()
    wm = WorkerManager(max_threads=3)
    for i in range(7):
        worker = wm.create_python_worker(sleeping_func, 'BOOM! {}'.format(i),
                                         secs=5)
        worker.sig_finished.connect(ready_print)
        worker.start()
    worker = wm.create_python_worker(sleeping_func, 'BOOM!', secs=5)
    worker.sig_finished.connect(ready_print)
    worker.start()

    worker = wm.create_process_worker(['conda', 'info', '--json'])
    worker.sig_finished.connect(ready_print)
    worker.start()
#    wm.terminate_all()
#    wm.terminate_all()

    sys.exit(app.exec_())


if __name__ == '__main__':  # pragma: no cover
    local_test()

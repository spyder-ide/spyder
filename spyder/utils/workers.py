# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------
"""
Worker manager and workers for running files long processes in non GUI
blocking threads.
"""

# Standard library imports
from collections import deque
import os
import sys

# Third party imports
from qtpy.QtCore import (QByteArray, QObject, QProcess, QThread, QTimer,
                         Signal)

# Local imports
from spyder.py3compat import PY2, to_text_string


WIN = os.name == 'nt'


def handle_qbytearray(obj, encoding):
    """Qt/Python2/3 compatibility helper."""
    if isinstance(obj, QByteArray):
        obj = obj.data()

    return to_text_string(obj, encoding=encoding)


class PythonWorker(QObject):
    """
    Generic python worker for running python code on threads.

    For running processes (via QProcess) use the ProcessWorker.
    """
    sig_started = Signal(object)
    sig_finished = Signal(object, object, object)  # worker, stdout, stderr

    def __init__(self, func, args, kwargs):
        """Generic python worker for running python code on threads."""
        super(PythonWorker, self).__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self._is_finished = False
        self._started = False

    def is_finished(self):
        """Return True if worker status is finished otherwise return False."""
        return self._is_finished

    def start(self):
        """Start the worker (emits sig_started signal with worker as arg)."""
        if not self._started:
            self.sig_started.emit(self)
            self._started = True

    def terminate(self):
        """Mark the worker as finished."""
        self._is_finished = True

    def _start(self):
        """Start process worker for given method args and kwargs."""
        error = None
        output = None

        try:
            output = self.func(*self.args, **self.kwargs)
        except Exception as err:
            error = err

        if not self._is_finished:
            self.sig_finished.emit(self, output, error)
        self._is_finished = True


class ProcessWorker(QObject):
    """Process worker based on a QProcess for non blocking UI."""

    sig_started = Signal(object)
    sig_finished = Signal(object, object, object)
    sig_partial = Signal(object, object, object)

    def __init__(self, cmd_list, environ=None):
        """
        Process worker based on a QProcess for non blocking UI.

        Parameters
        ----------
        cmd_list : list of str
            Command line arguments to execute.
        environ : dict
            Process environment,
        """
        super(ProcessWorker, self).__init__()
        self._result = None
        self._cmd_list = cmd_list
        self._fired = False
        self._communicate_first = False
        self._partial_stdout = None
        self._started = False

        self._timer = QTimer()
        self._process = QProcess()
        self._set_environment(environ)

        self._timer.setInterval(150)
        self._timer.timeout.connect(self._communicate)
        self._process.readyReadStandardOutput.connect(self._partial)

    def _get_encoding(self):
        """Return the encoding/codepage to use."""
        enco = 'utf-8'

        #  Currently only cp1252 is allowed?
        if WIN:
            import ctypes
            codepage = to_text_string(ctypes.cdll.kernel32.GetACP())
            # import locale
            # locale.getpreferredencoding()  # Differences?
            enco = 'cp' + codepage
        return enco

    def _set_environment(self, environ):
        """Set the environment on the QProcess."""
        if environ:
            q_environ = self._process.processEnvironment()
            for k, v in environ.items():
                q_environ.insert(k, v)
            self._process.setProcessEnvironment(q_environ)

    def _partial(self):
        """Callback for partial output."""
        raw_stdout = self._process.readAllStandardOutput()
        stdout = handle_qbytearray(raw_stdout, self._get_encoding())

        if self._partial_stdout is None:
            self._partial_stdout = stdout
        else:
            self._partial_stdout += stdout

        self.sig_partial.emit(self, stdout, None)

    def _communicate(self):
        """Callback for communicate."""
        if (not self._communicate_first and
                self._process.state() == QProcess.NotRunning):
            self.communicate()
        elif self._fired:
            self._timer.stop()

    def communicate(self):
        """Retrieve information."""
        self._communicate_first = True
        self._process.waitForFinished()

        enco = self._get_encoding()
        if self._partial_stdout is None:
            raw_stdout = self._process.readAllStandardOutput()
            stdout = handle_qbytearray(raw_stdout, enco)
        else:
            stdout = self._partial_stdout

        raw_stderr = self._process.readAllStandardError()
        stderr = handle_qbytearray(raw_stderr, enco)
        result = [stdout.encode(enco), stderr.encode(enco)]

        if PY2:
            stderr = stderr.decode()
        result[-1] = ''

        self._result = result

        if not self._fired:
            self.sig_finished.emit(self, result[0], result[-1])

        self._fired = True

        return result

    def close(self):
        """Close the running process."""
        self._process.close()

    def is_finished(self):
        """Return True if worker has finished processing."""
        return self._process.state() == QProcess.NotRunning and self._fired

    def _start(self):
        """Start process."""
        if not self._fired:
            self._partial_ouput = None
            self._process.start(self._cmd_list[0], self._cmd_list[1:])
            self._timer.start()

    def terminate(self):
        """Terminate running processes."""
        if self._process.state() == QProcess.Running:
            try:
                self._process.terminate()
            except Exception:
                pass
        self._fired = True

    def start(self):
        """Start worker."""
        if not self._started:
            self.sig_started.emit(self)
            self._started = True


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
        # Needed to avoud C++/python object errors
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
            #print('Queue: {0} Running: {1} Workers: {2} '
            #       'Threads: {3}'.format(len(self._queue_workers),
            #                                 self._running_threads,
            #                                 len(self._workers),
            #                                 len(self._threads)))
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

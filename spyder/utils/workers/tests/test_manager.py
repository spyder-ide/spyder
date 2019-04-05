# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------
"""
Tests for the worker manager.
"""

# Standard library imports
import time

# Local imports
from spyder.utils.workers import PythonWorker, WorkerManager


def sleeping_func(secs):
    """This method illustrates how the workers can be used."""
    time.sleep(secs)
    return secs


def test_process_worker(qtbot):
    def finished(worker, output, error):
        """Print worker output for tests."""
        assert worker.text in output.lower()

    wm = WorkerManager(max_threads=3)
    workers = []
    for i in range(3):
        worker = wm.create_process_worker(['git', '--help'])
        worker.sig_finished.connect(finished)
        worker.text = 'usage: git'
        workers.append(worker)

    w_last = workers[-1]     
    for worker in workers:
        worker.start()

    with qtbot.waitSignal(w_last.sig_finished, timeout=500):
        pass


def test_python_worker(qtbot):
    def finished(worker, output, error):
        """Print worker output for tests."""
        print(worker.secs)
        assert output == worker.secs

    wm = WorkerManager(max_threads=3)
    workers = []
    for i in range(6):
        secs = 0.500 + i/1000.0
        msecs = secs * 1000.0
        worker = wm.create_python_worker(sleeping_func, secs=secs)
        worker.secs = secs
        worker.sig_finished.connect(finished)
        workers.append(worker)

    w_first = workers[0]
    w_fourth = workers[3]
    
    for worker in workers:
        with qtbot.waitSignal(None, timeout=msecs/10.0, raising=False):
            pass
        worker.start()

    with qtbot.waitSignal(w_first.sig_finished, timeout=msecs*1.5):
        with qtbot.waitSignal(w_fourth.sig_finished, timeout=msecs*3.0):
            pass

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

    wm = WorkerManager(max_threads=1)
    worker = wm.create_process_worker(['git', '--help'])
    worker.sig_finished.connect(finished)
    worker.text = 'usage: git'

    with qtbot.waitSignal(worker.sig_finished, timeout=1000):
        worker.start()


def test_python_worker(qtbot):
    def finished(worker, output, error):
        """Print worker output for tests."""
        print(worker.secs)
        assert output == worker.secs

    wm = WorkerManager(max_threads=1)
    secs = 0.500
    msecs = 0.500 * 1000.0
    worker = wm.create_python_worker(sleeping_func, secs=secs)
    worker.secs = secs
    worker.sig_finished.connect(finished)

    with qtbot.waitSignal(worker.sig_finished, timeout=msecs*2.0):
        worker.start()

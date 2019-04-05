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

# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

import codecs
import os
import os.path as osp
import shutil
import tempfile
from textwrap import dedent

from flaky import flaky
import pytest
from qtpy import PYQT5
from qtpy.QtCore import Qt, QTimer
from qtpy.QtWidgets import QApplication

from spyder.py3compat import PY2
from spyder.plugins.ipythonconsole import (IPythonConsole,
                                           KernelConnectionDialog)
from spyder.utils.test import close_message_box

#==============================================================================
# Constants
#==============================================================================
SHELL_TIMEOUT = 20000


#==============================================================================
# Utillity Functions
#==============================================================================
def open_client_from_connection_info(connection_info, qtbot):
    top_level_widgets = QApplication.topLevelWidgets()
    for w in top_level_widgets:
        if isinstance(w, KernelConnectionDialog):
            w.cf.setText(connection_info)
            qtbot.keyClick(w, Qt.Key_Enter)


#==============================================================================
# Qt Test Fixtures
#==============================================================================
@pytest.fixture
def ipyconsole(request):
    widget = IPythonConsole(None, testing=True)
    widget.create_new_client()
    def close_widget():
        widget.close()
    request.addfinalizer(close_widget)
    widget.show()
    return widget


#==============================================================================
# Tests
#==============================================================================
def test_read_stderr(ipyconsole, qtbot):
    """
    Test the read operation of the stderr file of the kernel
    """

    shell = ipyconsole.get_current_shellwidget()
    client = ipyconsole.get_current_client()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Set contents of the stderr file of the kernel
    content = 'Test text'
    stderr_file = client.stderr_file
    codecs.open(stderr_file, 'w', 'cp437').write(content)
    # Assert that content is correct
    assert content == client._read_stderr()


@flaky(max_runs=10)
@pytest.mark.skipif(os.name == 'nt', reason="It times out on Windows")
def test_run_doctest(ipyconsole, qtbot):
    """
    Test that doctests can be run without problems
    """
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    code = dedent('''
    def add(x, y):
        """
        >>> add(1, 2)
        3
        >>> add(5.1, 2.2)
        7.3
        """
        return x + y
    ''')

    # Run code
    with qtbot.waitSignal(shell.executed):
        shell.execute(code)

    # Import doctest
    with qtbot.waitSignal(shell.executed):
        shell.execute('import doctest')

    # Run doctest
    with qtbot.waitSignal(shell.executed):
        shell.execute('doctest.testmod()')

    # Assert that doctests were run correctly
    assert "TestResults(failed=0, attempted=2)" in shell._control.toPlainText()


@flaky(max_runs=10)
@pytest.mark.skipif(os.name == 'nt' or (PY2 and PYQT5),
                    reason="It times out frequently")
def test_mpl_backend_change(ipyconsole, qtbot):
    """
    Test that Matplotlib backend is changed correctly when
    using the %matplotlib magic
    """
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Import Matplotlib
    with qtbot.waitSignal(shell.executed):
        shell.execute('import matplotlib.pyplot as plt')

    # Generate a plot
    with qtbot.waitSignal(shell.executed):
        shell.execute('plt.plot(range(10))')

    # Change backends
    with qtbot.waitSignal(shell.executed):
        shell.execute('%matplotlib tk')

    # Generate another plot
    with qtbot.waitSignal(shell.executed):
        shell.execute('plt.plot(range(10))')

    # Assert that there's a single inline plot in the console
    assert shell._control.toHtml().count('img src') == 1


@flaky(max_runs=10)
@pytest.mark.skipif(os.name == 'nt', reason="It times out on Windows")
def test_forced_restart_kernel(ipyconsole, qtbot):
    """
    Test that kernel is restarted if we force it do it
    during debugging
    """
    shell = ipyconsole.get_current_shellwidget()
    client = ipyconsole.get_current_client()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Do an assigment to verify that it's not there after restarting
    with qtbot.waitSignal(shell.executed):
        shell.execute('a = 10')

    # Generate a traceback and enter debugging mode
    with qtbot.waitSignal(shell.executed):
        shell.execute('1/0')

    shell.execute('%debug')
    qtbot.wait(500)

    # Force a kernel restart and wait until it's up again
    shell._prompt_html = None
    shell.silent_exec_input("1+1")  # The return type of this must be a dict!!
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    assert not shell.is_defined('a')


@flaky(max_runs=10)
@pytest.mark.skipif(os.name == 'nt', reason="It times out on Windows")
def test_restart_kernel(ipyconsole, qtbot):
    """
    Test that kernel is restarted correctly
    """
    shell = ipyconsole.get_current_shellwidget()
    client = ipyconsole.get_current_client()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    # Do an assigment to verify that it's not there after restarting
    with qtbot.waitSignal(shell.executed):
        shell.execute('a = 10')

    # Restart kernel and wait until it's up again
    shell._prompt_html = None
    QTimer.singleShot(1000, lambda: close_message_box(qtbot))
    client.restart_kernel()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    assert not shell.is_defined('a')


@flaky(max_runs=10)
@pytest.mark.skipif(os.name == 'nt', reason="It times out on Windows")
def test_load_kernel_file_from_id(ipyconsole, qtbot):
    """
    Test that a new client is created using its id
    """
    shell = ipyconsole.get_current_shellwidget()
    client = ipyconsole.get_current_client()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    connection_file = osp.basename(client.connection_file)
    id_ = connection_file.split('kernel-')[-1].split('.json')[0]

    QTimer.singleShot(2000, lambda: open_client_from_connection_info(
                                        id_, qtbot))
    ipyconsole.create_client_for_kernel()
    qtbot.wait(1000)

    new_client = ipyconsole.get_clients()[1]
    assert new_client.name == '1/B'


@flaky(max_runs=10)
@pytest.mark.skipif(os.name == 'nt', reason="It times out on Windows")
def test_load_kernel_file_from_location(ipyconsole, qtbot):
    """
    Test that a new client is created using a connection file
    placed in a different location from jupyter_runtime_dir
    """
    shell = ipyconsole.get_current_shellwidget()
    client = ipyconsole.get_current_client()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    connection_file = osp.join(tempfile.gettempdir(),
                               osp.basename(client.connection_file))
    shutil.copy2(client.connection_file, connection_file)

    QTimer.singleShot(2000, lambda: open_client_from_connection_info(
                                        connection_file,
                                        qtbot))
    ipyconsole.create_client_for_kernel()
    qtbot.wait(1000)

    assert len(ipyconsole.get_clients()) == 2


@flaky(max_runs=10)
@pytest.mark.skipif(os.name == 'nt', reason="It times out on Windows")
def test_load_kernel_file(ipyconsole, qtbot):
    """
    Test that a new client is created using the connection file
    of an existing client
    """
    shell = ipyconsole.get_current_shellwidget()
    client = ipyconsole.get_current_client()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    QTimer.singleShot(2000, lambda: open_client_from_connection_info(
                                        client.connection_file,
                                        qtbot))
    ipyconsole.create_client_for_kernel()
    qtbot.wait(1000)

    new_client = ipyconsole.get_clients()[1]
    new_shell = new_client.shellwidget
    with qtbot.waitSignal(new_shell.executed):
        new_shell.execute('a = 10')

    assert new_client.name == '1/B'
    assert shell.get_value('a') == new_shell.get_value('a')


@flaky(max_runs=10)
@pytest.mark.skipif(os.name == 'nt', reason="It times out on Windows")
def test_sys_argv_clear(ipyconsole, qtbot):
    """Test that sys.argv is cleared up correctly"""
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    shell.execute('import sys; A = sys.argv')
    argv = shell.get_value("A")
    assert argv == ['']


if __name__ == "__main__":
    pytest.main()

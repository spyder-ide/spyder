# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

import os
import os.path as osp
import shutil
import tempfile

from flaky import flaky
import pytest
from qtpy.QtCore import Qt, QTimer
from qtpy.QtWidgets import QApplication, QMessageBox

from spyder.plugins.ipythonconsole import (IPythonConsole,
                                           KernelConnectionDialog)


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


def restart_kernel(qtbot):
    top_level_widgets = QApplication.topLevelWidgets()
    for w in top_level_widgets:
        if isinstance(w, QMessageBox):
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
#@flaky(max_runs=10)
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
    shell.execute('a = 10')
    qtbot.wait(500)

    # Generate a traceback and enter debugging mode
    shell.execute('1/0')
    qtbot.wait(500)
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
    shell.execute('a = 10')
    qtbot.wait(500)

    # Restart kernel and wait until it's up again
    shell._prompt_html = None
    QTimer.singleShot(1000, lambda: restart_kernel(qtbot))
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
    new_shell.execute('a = 10')
    qtbot.wait(500)

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

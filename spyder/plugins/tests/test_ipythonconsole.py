# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

import pytest
from qtpy.QtCore import Qt, QTimer
from qtpy.QtWidgets import QApplication, QDialog

from spyder.plugins.ipythonconsole import IPythonConsole


#==============================================================================
# Constants
#==============================================================================
SHELL_TIMEOUT = 30000


#==============================================================================
# Utillity Functions
#==============================================================================
def open_client_from_connection_file(connection_file, qtbot):
    top_level_widgets = QApplication.topLevelWidgets()
    for w in top_level_widgets:
        if isinstance(w, QDialog):
            w.cf.setText(connection_file)
            qtbot.keyClick(w, Qt.Key_Enter)


#==============================================================================
# Qt Test Fixtures
#==============================================================================
@pytest.fixture
def ipyconsole():
    widget = IPythonConsole(None, testing=True)
    widget.create_new_client()
    widget.show()
    return widget


#==============================================================================
# Tests
#==============================================================================
def test_load_kernel_file(ipyconsole, qtbot):
    """
    Test that a new client is created using the connection file
    of an existing client
    """
    shell = ipyconsole.get_current_shellwidget()
    client = ipyconsole.get_current_client()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    QTimer.singleShot(2000, lambda: open_client_from_connection_file(
                                        client.connection_file,
                                        qtbot))
    ipyconsole.create_client_for_kernel()

    new_client = ipyconsole.get_clients()[1]
    new_shell = new_client.shellwidget
    qtbot.waitUntil(lambda: new_shell._prompt_html is not None, timeout=SHELL_TIMEOUT)
    new_shell.execute('a = 10')

    assert new_client.name == '1/B'
    assert shell.get_value('a') == new_shell.get_value('a')

    ipyconsole.close()


def test_sys_argv_clear(ipyconsole, qtbot):
    """Test that sys.argv is cleared up correctly"""
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT)

    shell.execute('import sys; A = sys.argv')
    argv = shell.get_value("A")
    assert argv == ['']

    ipyconsole.close()

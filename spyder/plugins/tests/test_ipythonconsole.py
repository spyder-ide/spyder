# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

import os

import mock
import pytest
from qtpy.QtCore import Qt
from pytestqt import qtbot
from spyder.py3compat import to_text_string
from spyder.plugins.ipythonconsole import (IPythonConsole,
                                           KernelConnectionDialog)
from qtpy.QtWidgets import QDialogButtonBox

# Qt Test Fixtures
#--------------------------------
@pytest.fixture
def ipyconsole():
    widget = IPythonConsole(None, testing=True)
    widget.create_new_client()
    return widget

@pytest.fixture
def kernelconn(qtbot):
    widget = KernelConnectionDialog(None)
    qtbot.addWidget(widget)
    return widget

# Tests
#-------------------------------
@pytest.mark.skipif(os.name == 'nt', reason="It's timing out on Windows")
def test_sys_argv_clear(ipyconsole, qtbot):
    shell = ipyconsole.get_current_shellwidget()
    client = ipyconsole.get_current_client()

    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=6000)
    shell.execute('import sys; A = sys.argv')
    argv = shell.get_value("A")
    assert argv == ['']

def test_load_kernel_id(kernelconn, qtbot):
    _id = "testkernel"
    kernelconn.cf.setText(_id)
    qtbot.keyPress(kernelconn, Qt.Key_Return)
    # mock.patch.object(kernelconn, 'accept_btns', return_value=QDialogButtonBox.Ok)
    # qtbot.keyPress(kernelconn.accept_btns, Qt.Key_Return)
    # kernelconn.exec_()
    # qtbot.mouseClick(kernelconn.accept_btns, Qt.LeftButton)
    # kernelconn.accept()
    result = KernelConnectionDialog.get_connection_parameters(
                    dialog=kernelconn
             )
    path, _, _, _, _ = result
    print(path)
    assert False


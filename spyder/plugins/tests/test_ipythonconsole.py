# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

import os
import os.path as osp

import mock
import pytest
from pytestqt import qtbot
from qtpy.QtCore import Qt, QTimer
from spyder.py3compat import to_text_string
from spyder.plugins.ipythonconsole import (IPythonConsole,
                                           KernelConnectionDialog)
from qtpy.QtWidgets import QDialogButtonBox
from jupyter_core.paths import jupyter_config_dir, jupyter_runtime_dir

# Utillity Functions
#--------------------------------
def dialog_interaction(kernelconn, _id, qtbot):
    kernelconn.cf.setText(_id)
    qtbot.keyPress(kernelconn, Qt.Key_Return)

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
    widget.hide()
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

@pytest.mark.skipif(os.name == 'nt', reason="It's timing out on Windows")
def test_load_kernel_id(kernelconn, qtbot):
    dest_path = jupyter_runtime_dir()
    _id = "testkernel"

    QTimer.singleShot(2000, lambda: dialog_interaction(kernelconn, _id, qtbot))

    result = KernelConnectionDialog.get_connection_parameters(
                    dialog=kernelconn
             )
    path, _, _, _, _ = result
    path_dir, filename = osp.dirname(path), osp.basename(path)
    assert path_dir == dest_path and filename == 'kernel-%s.json' % (_id)

@pytest.mark.skipif(os.name == 'nt', reason="It's timing out on Windows")
def test_load_kernel_file(kernelconn, qtbot):
    path = jupyter_runtime_dir()
    file = osp.join(path, 'some_id.json')
    QTimer.singleShot(2000, lambda: dialog_interaction(kernelconn, file, qtbot))
    result = KernelConnectionDialog.get_connection_parameters(
                    dialog=kernelconn
             )
    location, _, _, _, _ = result
    assert location == file

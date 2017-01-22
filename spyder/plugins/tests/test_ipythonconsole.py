# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

import pytest
from qtpy.QtCore import Qt
from pytestqt import qtbot
from spyder.py3compat import to_text_string
from spyder.plugins.ipythonconsole import IPythonConsole

# Qt Test Fixtures
#--------------------------------
@pytest.fixture
def botipython(qtbot):
    widget = IPythonConsole(None, testing=True)
    widget.create_new_client()
    qtbot.addWidget(widget)
    widget.show()
    return qtbot, widget

# Tests
#-------------------------------
def test_sys_argv_clear(botipython):
    qtbot, ipy = botipython
    shell = ipy.get_current_shellwidget()
    client = ipy.get_current_client()

    with qtbot.waitSignal(client.shell_ready, timeout=6000) as blocker:
        shell.silent_exec_method('import sys;A = len(sys.argv)')
    len_argv = shell.get_value("A")
    while len_argv is None:
        shell.silent_exec_method('import sys;A = len(sys.argv)')
        qtbot.keyClicks(client.get_control(), 'import sys;A = len(sys.argv)')
        qtbot.keyPress(client.get_control(), Qt.Key_Return)
        len_argv = shell.get_value("A")
    assert len_argv == 1


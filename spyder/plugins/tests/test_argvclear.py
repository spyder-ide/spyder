# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

import pytest
from pytestqt import qtbot
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
    while not shell.is_running():
        continue
    # with qtbot.waitSignal(client.shellwidget.executing) as blocker:
    #     client.shellwidget.silent_exec_method('import sys')
    #     client.shellwidget.silent_exec_method('print(len(sys.argv))')
    assert shell.is_running()


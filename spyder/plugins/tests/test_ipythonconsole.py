# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

import os

import pytest
from qtpy.QtCore import Qt
from pytestqt import qtbot
from spyder.py3compat import to_text_string
from spyder.plugins.ipythonconsole import IPythonConsole


# Qt Test Fixtures
#--------------------------------
@pytest.fixture
def ipyconsole():
    widget = IPythonConsole(None, testing=True)
    widget.create_new_client()
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

# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#
"""Tests for the Editor plugin."""

# Third party imports
import pytest
import os
import os.path as osp
from flaky import flaky

try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock  # Python 2

from qtpy.QtWidgets import QWidget, QApplication
from qtpy.QtCore import Qt

from spyder.utils.introspection.jedi_plugin import JEDI_010
from spyder.utils.qthelpers import qapplication

# Location of this file
LOCATION = osp.realpath(osp.join(os.getcwd(), osp.dirname(__file__)))


@pytest.fixture
def setup_editor(qtbot, monkeypatch):
    """Set up the Editor plugin."""
    app = qapplication()
    os.environ['SPY_TEST_USE_INTROSPECTION'] = 'True'
    monkeypatch.setattr('spyder.dependencies', Mock())
    from spyder.plugins.editor import Editor

    monkeypatch.setattr('spyder.plugins.editor.add_actions', Mock())

    class MainMock(QWidget):
        def __getattr__(self, attr):
            if attr.endswith('actions'):
                return []
            else:
                return Mock()

        def get_spyder_pythonpath(*args):
            return []

    editor = Editor(MainMock())
    qtbot.addWidget(editor)
    editor.show()
    editor.new(fname="test.py", text="")
    editor.introspector.set_editor_widget(editor.editorstacks[0])

    yield editor, qtbot
    # teardown
    os.environ['SPY_TEST_USE_INTROSPECTION'] = 'False'
    editor.introspector.plugin_manager.close()


@flaky(max_runs=3)
@pytest.mark.skipif(not JEDI_010,
                    reason="This feature is only supported in jedy >= 0.10")
def test_introspection(setup_editor):
    """Validate changing path in introspection plugins."""
    editor, qtbot = setup_editor
    code_editor = editor.get_focus_widget()
    completion = code_editor.completion_widget

    # Set cursor to start
    code_editor.go_to_line(1)

    # Complete fr --> from
    qtbot.keyClicks(code_editor, 'fr')
    qtbot.wait(5000)

    # press tab and get completions
    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=5000) as sig:
        qtbot.keyPress(code_editor, Qt.Key_Tab)
    assert "from" in sig.args[0]

    # enter should accept first completion
    qtbot.keyPress(completion, Qt.Key_Enter, delay=1000)
    assert code_editor.toPlainText() == 'from\n'

    # Modify PYTHONPATH
    editor.introspector.change_extra_path([LOCATION])
    qtbot.wait(10000)

    # Type 'from test' and try to get completion
    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyClicks(code_editor, ' test_')
        qtbot.keyPress(code_editor, Qt.Key_Tab)
    assert "test_editor_introspection" in sig.args[0]

# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#
"""Tests for the Editor plugin."""

# Standard library imports
import os
import os.path as osp

# Third party imports
import pytest
try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock  # Python 2
from qtpy.QtWidgets import QWidget, QApplication
from qtpy.QtCore import Qt

# Local imports
from spyder.utils.qthelpers import qapplication
from spyder.py3compat import PY2
from spyder.plugins.lspmanager import LSPManager

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
        def __init__(self, parent):
            QWidget.__init__(self, parent)
            self.lspmanager = LSPManager(parent=self)

        def __getattr__(self, attr):
            if attr.endswith('actions'):
                return []
            if attr == 'lspmanager':
                return self.lspmanager
            else:
                return Mock()

        def get_spyder_pythonpath(*args):
            return []

    editor = Editor(MainMock(None))
    editor.register_plugin()
    qtbot.addWidget(editor)
    editor.show()
    with qtbot.waitSignal(editor.sig_lsp_notification, timeout=30000):
        editor.new(fname="test.py", text="")
    # editor.introspector.set_editor_widget(editor.editorstacks[0])
    code_editor = editor.get_focus_widget()
    with qtbot.waitSignal(code_editor.lsp_response_signal, timeout=30000):
        code_editor.document_did_open()

    yield editor, qtbot
    # teardown
    os.environ['SPY_TEST_USE_INTROSPECTION'] = 'False'
    editor.main.lspmanager.closing_plugin()


@pytest.mark.slow
@pytest.mark.skipif(PY2, reason="Segfaults with other tests on Py2.")
@pytest.mark.skipif(os.name == 'nt' and not PY2,
                    reason="Times out on AppVeyor and fails on PY3")
def test_introspection(setup_editor):
    """Validate changing path in introspection plugins."""
    editor, qtbot = setup_editor
    code_editor = editor.get_focus_widget()
    completion = code_editor.completion_widget

    # Set cursor to start
    code_editor.go_to_line(1)

    # Complete fr --> from
    qtbot.keyClicks(code_editor, 'fr')
    qtbot.wait(20000)

    # press tab and get completions
    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyPress(code_editor, Qt.Key_Tab)
    assert "from" in [x['label'] for x in sig.args[0]]

    # enter should accept first completion
    qtbot.keyPress(completion, Qt.Key_Enter, delay=1000)
    assert code_editor.toPlainText() == 'from\n'

    # Modify PYTHONPATH
    # editor.introspector.change_extra_path([LOCATION])
    # qtbot.wait(10000)
    #
    # # Type 'from test' and try to get completion
    # with qtbot.waitSignal(completion.sig_show_completions,
    #                       timeout=10000) as sig:
    #     qtbot.keyClicks(code_editor, ' test_')
    #     qtbot.keyPress(code_editor, Qt.Key_Tab)
    # assert "test_editor_introspection" in sig.args[0]

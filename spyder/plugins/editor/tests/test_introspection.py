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
import pytestqt
try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock  # Python 2
from qtpy.QtWidgets import QWidget, QApplication
from qtpy.QtCore import Qt

# Local imports
from spyder.utils.qthelpers import qapplication
from spyder.py3compat import PY2
from spyder.plugins.editor.lsp.manager import LSPManager
from spyder.utils.misc import getcwd_or_home


# Location of this file
LOCATION = osp.realpath(osp.join(os.getcwd(), osp.dirname(__file__)))


@pytest.fixture
def setup_editor(qtbot, monkeypatch):
    """Set up the Editor plugin."""
    app = qapplication()
    os.environ['SPY_TEST_USE_INTROSPECTION'] = 'True'
    monkeypatch.setattr('spyder.dependencies', Mock())
    from spyder.plugins.editor.plugin import Editor

    monkeypatch.setattr('spyder.plugins.editor.plugin.add_actions', Mock())

    class MainMock(QWidget):
        def __init__(self, parent):
            QWidget.__init__(self, parent)
            self.lspmanager = LSPManager(parent=self)
            self.projects = None

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
    editor.main.lspmanager.shutdown()


@pytest.mark.slow
def test_space_completion(setup_editor):
    """Validate completion's space character handling."""
    editor, qtbot = setup_editor
    code_editor = editor.get_focus_widget()
    completion = code_editor.completion_widget

    # Set cursor to start
    code_editor.go_to_line(1)

    # Complete from numpy --> from numpy import
    qtbot.keyClicks(code_editor, 'from numpy ')
    qtbot.wait(20000)

    # press tab and get completions
    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyPress(code_editor, Qt.Key_Tab)
    assert "import" in [x['label'] for x in sig.args[0]]

    # enter should accept first completion
    qtbot.keyPress(completion, Qt.Key_Enter, delay=1000)
    assert code_editor.toPlainText() == 'from numpy import\n'


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

    # Complete import mat--> import math
    qtbot.keyClicks(code_editor, 'import mat')
    qtbot.wait(20000)

    # press tab and get completions
    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyPress(code_editor, Qt.Key_Tab)
    assert "math" in [x['label'] for x in sig.args[0]]

    # enter should accept first completion
    qtbot.keyPress(completion, Qt.Key_Enter, delay=1000)
    assert code_editor.toPlainText() == 'import math\n'

    # enter for new line
    qtbot.keyPress(code_editor, Qt.Key_Enter, delay=1000)

    # Complete math.d() -> math.degrees()
    qtbot.keyClicks(code_editor, 'math.d')
    qtbot.wait(20000)

    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyPress(code_editor, Qt.Key_Tab)
    assert "degrees(x)" in [x['label'] for x in sig.args[0]]

    qtbot.keyPress(completion, Qt.Key_Enter, delay=1000)
    assert code_editor.toPlainText() == 'import math\nmath.degrees\n'

    # enter for new line
    qtbot.keyPress(code_editor, Qt.Key_Enter, delay=1000)

    # Complete math.d() -> math.degrees()
    qtbot.keyClicks(code_editor, 'math.d(')
    qtbot.keyPress(code_editor, Qt.Key_Left, delay=1000)
    qtbot.keyClicks(code_editor, 'e')
    qtbot.wait(20000)

    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyPress(code_editor, Qt.Key_Tab)
    assert "degrees(x)" in [x['label'] for x in sig.args[0]]

    qtbot.keyPress(completion, Qt.Key_Enter, delay=1000)

    # right for () + enter for new line
    qtbot.keyPress(code_editor, Qt.Key_Right, delay=1000)
    qtbot.keyPress(code_editor, Qt.Key_Right, delay=1000)
    qtbot.keyPress(code_editor, Qt.Key_Enter, delay=1000)

    # Complete math.a <tab> ... s <enter> to math.asin
    qtbot.keyClicks(code_editor, 'math.a')
    qtbot.wait(20000)
    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyPress(code_editor, Qt.Key_Tab)
    assert "asin(x)" in [x['label'] for x in sig.args[0]]
    qtbot.keyClicks(completion, 's')
    qtbot.keyPress(completion, Qt.Key_Enter, delay=1000)

    # enter for new line
    qtbot.keyPress(code_editor, Qt.Key_Enter, delay=1000)

    # Complete math.a <tab><enter> ... <enter> to math.acos
    qtbot.keyClicks(code_editor, 'math.a')
    qtbot.wait(20000)
    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyPress(code_editor, Qt.Key_Tab)
        qtbot.keyPress(code_editor, Qt.Key_Enter)
    assert "acos(x)" in [x['label'] for x in sig.args[0]]
    qtbot.keyPress(completion, Qt.Key_Enter, delay=1000)

    qtbot.keyPress(code_editor, Qt.Key_Enter, delay=1000)

    # Complete math.a <tab> s ...<enter> to math.asin
    qtbot.keyClicks(code_editor, 'math.a')
    qtbot.wait(20000)
    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyPress(code_editor, Qt.Key_Tab)
        qtbot.keyPress(code_editor, 's')
    assert "asin(x)" in [x['label'] for x in sig.args[0]]
    qtbot.keyPress(completion, Qt.Key_Enter, delay=1000)

    # Check math.a <tab> <backspace> doesn't emit sig_show_completions
    qtbot.keyPress(code_editor, Qt.Key_Right, delay=1000)
    qtbot.keyClicks(code_editor, 'math.a')
    qtbot.wait(20000)
    try:
        with qtbot.waitSignal(completion.sig_show_completions,
                              timeout=10000) as sig:
            qtbot.keyPress(code_editor, Qt.Key_Tab)
            qtbot.keyPress(code_editor, Qt.Key_Backspace)
        raise RuntimeError("The signal should not have been recieved!")
    except pytestqt.exceptions.TimeoutError:
        pass

    assert code_editor.toPlainText() == 'import math\nmath.degrees\n'\
                                        'math.degrees()\nmath.asin\n'\
                                        'math.acos\nmath.asin\nmath.\n'

    # Modify PYTHONPATH
    # editor.introspector.change_extra_path([LOCATION])
    # qtbot.wait(10000)
    #
    # # Type 'from test' and try to get completion
    # with qtbot.waitSignal(completion.sig_show_completions,
    #                       timeout=10000) as sig:
    #     qtbot.keyClicks(code_editor, ' test_')
    #     qtbot.keyPress(code_editor, Qt.Key_Tab)
    # assert "test_introspection" in sig.args[0]

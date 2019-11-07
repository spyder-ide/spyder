# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""Tests for code completion."""

# Standard library imports
import os
import os.path as osp
import random
import textwrap
import sys

# Third party imports
from flaky import flaky
import pytest
import pytestqt

from qtpy.QtCore import Qt
from qtpy.QtGui import QTextCursor

try:
    from rtree import index
    rtree_available = True
except Exception:
    rtree_available = False

# Local imports
from spyder.plugins.completion.languageserver import (
    LSPRequestTypes, CompletionItemKind)
from spyder.plugins.completion.kite.providers.document import KITE_COMPLETION
from spyder.py3compat import PY2
from spyder.config.manager import CONF


# Location of this file
LOCATION = osp.realpath(osp.join(os.getcwd(), osp.dirname(__file__)))


@pytest.mark.slow
@pytest.mark.first
def test_space_completion(lsp_codeeditor, qtbot):
    """Validate completion's space character handling."""
    code_editor, _ = lsp_codeeditor
    code_editor.toggle_automatic_completions(False)
    code_editor.toggle_code_snippets(False)
    CONF.set('editor', 'completions_wait_for_ms', 0)

    completion = code_editor.completion_widget

    # Set cursor to start
    code_editor.go_to_line(1)

    # Complete from numpy --> from numpy import
    qtbot.keyClicks(code_editor, 'from numpy ')
    with qtbot.waitSignal(code_editor.lsp_response_signal, timeout=30000):
        code_editor.document_did_change()

    # press tab and get completions
    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyPress(code_editor, Qt.Key_Tab)

    assert "import" in [x['label'] for x in sig.args[0]]

    assert code_editor.toPlainText() == 'from numpy import'
    assert not completion.isVisible()

    code_editor.toggle_automatic_completions(True)
    code_editor.toggle_code_snippets(True)


@pytest.mark.slow
@pytest.mark.first
@flaky(max_runs=5)
def test_hide_widget_completion(lsp_codeeditor, qtbot):
    """Validate hiding completion widget after a delimeter or operator."""
    code_editor, _ = lsp_codeeditor
    completion = code_editor.completion_widget

    delimiters = ['(', ')', '[', ']', '{', '}', ',', ':', ';', '@', '=', '->',
                  '+=', '-=', '*=', '/=', '//=', '%=', '@=', '&=', '|=', '^=',
                  '>>=', '<<=', '**=']

    code_editor.toggle_automatic_completions(False)
    code_editor.toggle_code_snippets(False)

    # Set cursor to start
    code_editor.go_to_line(1)

    # Complete from numpy import --> from numpy import ?
    qtbot.keyClicks(code_editor, 'from numpy import ')
    with qtbot.waitSignal(code_editor.lsp_response_signal, timeout=30000):
        code_editor.document_did_change()

    # press tab and get completions
    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyPress(code_editor, Qt.Key_Tab)

    # Check the completion widget is visible
    assert completion.isHidden() is False

    # Write a random delimeter on the code editor
    delimeter = random.choice(delimiters)
    qtbot.keyClicks(code_editor, delimeter)

    # Check the completion widget is not visible
    assert completion.isHidden() is True

    code_editor.toggle_automatic_completions(True)
    code_editor.toggle_code_snippets(True)


@pytest.mark.slow
@pytest.mark.first
@flaky(max_runs=5)
def test_automatic_completions(lsp_codeeditor, qtbot):
    """Test on-the-fly completions."""
    code_editor, _ = lsp_codeeditor
    completion = code_editor.completion_widget
    code_editor.toggle_code_snippets(False)

    # Set cursor to start
    code_editor.go_to_line(1)

    # Complete f -> from
    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyClicks(code_editor, 'f')

    assert "from" in [x['label'] for x in sig.args[0]]
    # qtbot.keyPress(code_editor, Qt.Key_Tab)

    qtbot.keyClicks(code_editor, 'rom')

    # Due to automatic completion, the completion widget may appear before
    stop = False
    while not stop:
        try:
            with qtbot.waitSignal(completion.sig_show_completions,
                                  timeout=5000) as sig:
                pass
            code_editor.completion_widget.hide()
        except Exception:
            stop = True

    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyClicks(code_editor, ' n')

    assert "ntpath" in [x['label'] for x in sig.args[0]]

    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyClicks(code_editor, 'ump')

    assert "numpy" in [x['label'] for x in sig.args[0]]

    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyClicks(code_editor, 'y')

    # Due to automatic completion, the completion widget may appear before
    stop = False
    while not stop:
        try:
            with qtbot.waitSignal(completion.sig_show_completions,
                                  timeout=5000) as sig:
                pass
            code_editor.completion_widget.hide()
        except Exception:
            stop = True

    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyClicks(code_editor, ' imp')

    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyPress(code_editor, Qt.Key_Tab)

    assert code_editor.toPlainText() == 'from numpy import'

    # Due to automatic completion, the completion widget may appear before
    stop = False
    while not stop:
        try:
            with qtbot.waitSignal(completion.sig_show_completions,
                                  timeout=5000) as sig:
                pass
            code_editor.completion_widget.hide()
        except Exception:
            stop = True

    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyClicks(code_editor, ' r')

    assert "random" in [x['label'] for x in sig.args[0]]
    code_editor.toggle_code_snippets(True)


@pytest.mark.slow
@flaky(max_runs=3)
def test_automatic_completions_parens_bug(lsp_codeeditor, qtbot):
    """
    Test on-the-fly completions.

    Autocompletions for variables don't work inside function calls.

    See: spyder-ide/spyder#10448
    """
    code_editor, _ = lsp_codeeditor
    completion = code_editor.completion_widget
    code_editor.toggle_code_snippets(False)

    # Parens:
    # Set cursor to start
    code_editor.set_text('my_list = [1, 2, 3]\nlist_copy = list((my))')
    cursor = code_editor.textCursor()
    code_editor.moveCursor(cursor.End)

    # Move cursor next to list((my$))
    qtbot.keyPress(code_editor, Qt.Key_Left)
    qtbot.keyPress(code_editor, Qt.Key_Left)
    qtbot.wait(500)

    # Complete my_ -> my_list
    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=5000) as sig:
        qtbot.keyClicks(code_editor, '_')

    assert "my_list" in [x['label'] for x in sig.args[0]]

    # Square braces:
    # Set cursor to start
    code_editor.set_text('my_dic = {1: 1, 2: 2}\nonesee = 1\none = my_dic[on]')
    cursor = code_editor.textCursor()
    code_editor.moveCursor(cursor.End)

    # Move cursor next to my_dic[on$]
    qtbot.keyPress(code_editor, Qt.Key_Left)
    qtbot.wait(500)

    # Complete one -> onesee
    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=5000) as sig:
        qtbot.keyClicks(code_editor, 'e')

    assert "onesee" in [x['label'] for x in sig.args[0]]

    # Curly braces:
    # Set cursor to start
    code_editor.set_text('my_dic = {1: 1, 2: 2}\nonesee = 1\none = {on}')
    cursor = code_editor.textCursor()
    code_editor.moveCursor(cursor.End)

    # Move cursor next to {on*}
    qtbot.keyPress(code_editor, Qt.Key_Left)
    qtbot.wait(500)

    # Complete one -> onesee
    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=5000) as sig:
        qtbot.keyClicks(code_editor, 'e')

    assert "onesee" in [x['label'] for x in sig.args[0]]


@pytest.mark.slow
@pytest.mark.first
@flaky(max_runs=5)
def test_completions(lsp_codeeditor, qtbot):
    """Exercise code completion in several ways."""
    code_editor, _ = lsp_codeeditor
    completion = code_editor.completion_widget

    code_editor.toggle_automatic_completions(False)
    code_editor.toggle_code_snippets(False)

    # Set cursor to start
    code_editor.go_to_line(1)

    # Complete import mat--> import math
    qtbot.keyClicks(code_editor, 'import mat')
    with qtbot.waitSignal(code_editor.lsp_response_signal, timeout=30000):
        code_editor.document_did_change()

    # press tab and get completions
    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyPress(code_editor, Qt.Key_Tab)
    assert "math" in [x['label'] for x in sig.args[0]]

    # enter should accept first completion
    qtbot.keyPress(completion, Qt.Key_Enter, delay=300)
    assert code_editor.toPlainText() == 'import math'

    # enter for new line
    qtbot.keyPress(code_editor, Qt.Key_Enter, delay=300)

    # Complete math.h() -> math.hypot()
    qtbot.keyClicks(code_editor, 'math.h')
    with qtbot.waitSignal(code_editor.lsp_response_signal, timeout=30000):
        code_editor.document_did_change()

    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyPress(code_editor, Qt.Key_Tab)
    if PY2:
        assert "hypot(x, y)" in [x['label'] for x in sig.args[0]]
    else:
        assert [x['label'] for x in sig.args[0]][0] in ["hypot(x, y)",
                                                        "hypot(*coordinates)"]

    assert code_editor.toPlainText() == 'import math\nmath.hypot'

    # enter for new line
    qtbot.keyPress(code_editor, Qt.Key_Enter, delay=300)

    # Complete math.h() -> math.degrees()
    qtbot.keyClicks(code_editor, 'math.h(')
    qtbot.keyPress(code_editor, Qt.Key_Left, delay=300)
    qtbot.keyClicks(code_editor, 'y')
    with qtbot.waitSignal(code_editor.lsp_response_signal, timeout=30000):
        code_editor.document_did_change()

    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyPress(code_editor, Qt.Key_Tab)
    if PY2:
        assert "hypot(x, y)" in [x['label'] for x in sig.args[0]]
    else:
        assert [x['label'] for x in sig.args[0]][0] in ["hypot(x, y)",
                                                        "hypot(*coordinates)"]

    # right for () + enter for new line
    qtbot.keyPress(code_editor, Qt.Key_Right, delay=300)
    qtbot.keyPress(code_editor, Qt.Key_Right, delay=300)
    qtbot.keyPress(code_editor, Qt.Key_Enter, delay=300)
    assert code_editor.toPlainText() == 'import math\nmath.hypot\n'\
                                        'math.hypot()\n'

    # Complete math.a <tab> ... s <enter> to math.asin
    qtbot.keyClicks(code_editor, 'math.a')
    with qtbot.waitSignal(code_editor.lsp_response_signal, timeout=30000):
        code_editor.document_did_change()

    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyPress(code_editor, Qt.Key_Tab)
    assert "asin(x)" in [x['label'] for x in sig.args[0]]
    # Test if the list is updated
    assert "acos(x)" == completion.completion_list[0]['label']
    qtbot.keyClicks(completion, 's')
    data = completion.item(0).data(Qt.UserRole)
    assert "asin" == data['insertText']
    qtbot.keyPress(completion, Qt.Key_Enter, delay=300)

    # enter for new line
    qtbot.keyPress(code_editor, Qt.Key_Enter, delay=300)
    assert code_editor.toPlainText() == 'import math\nmath.hypot\n'\
                                        'math.hypot()\nmath.asin\n'

    # Check can get list back
    qtbot.keyClicks(code_editor, 'math.f')
    with qtbot.waitSignal(code_editor.lsp_response_signal, timeout=30000):
        code_editor.document_did_change()

    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyPress(code_editor, Qt.Key_Tab)
    assert completion.count() == 6
    assert "floor(x)" in [x['label'] for x in sig.args[0]]
    qtbot.keyClicks(completion, 'l')
    assert completion.count() == 1
    qtbot.keyPress(completion, Qt.Key_Backspace)
    assert completion.count() == 6

    # enter for new line
    qtbot.keyPress(code_editor, Qt.Key_Enter, delay=300)
    assert code_editor.toPlainText() == 'import math\nmath.hypot\n'\
                                        'math.hypot()\nmath.asin\n'\
                                        'math.f\n'

    # Complete math.a <tab> s ...<enter> to math.asin
    qtbot.keyClicks(code_editor, 'math.a')
    with qtbot.waitSignal(code_editor.lsp_response_signal, timeout=30000):
        code_editor.document_did_change()

    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyPress(code_editor, Qt.Key_Tab)
        qtbot.keyPress(code_editor, 's')
    assert "asin(x)" in [x['label'] for x in sig.args[0]]
    qtbot.keyPress(completion, Qt.Key_Enter, delay=300)

    # enter for new line
    qtbot.keyPress(code_editor, Qt.Key_Enter, delay=300)
    assert code_editor.toPlainText() == 'import math\nmath.hypot\n'\
                                        'math.hypot()\nmath.asin\n'\
                                        'math.f\nmath.asin\n'

    # Complete math.a|angle <tab> s ...<enter> to math.asin|angle
    qtbot.keyClicks(code_editor, 'math.aangle')
    for i in range(len('angle')):
        qtbot.keyClick(code_editor, Qt.Key_Left)

    with qtbot.waitSignal(code_editor.lsp_response_signal, timeout=30000):
        code_editor.document_did_change()

    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyPress(code_editor, Qt.Key_Tab)
        qtbot.keyPress(code_editor, 's')
    assert "asin(x)" in [x['label'] for x in sig.args[0]]
    qtbot.keyPress(completion, Qt.Key_Enter, delay=300)
    for i in range(len('angle')):
        qtbot.keyClick(code_editor, Qt.Key_Right)

    qtbot.keyPress(code_editor, Qt.Key_Enter, delay=300)
    assert code_editor.toPlainText() == 'import math\nmath.hypot\n'\
                                        'math.hypot()\nmath.asin\n'\
                                        'math.f\nmath.asin\n'\
                                        'math.asinangle\n'

    # Check math.a <tab> <backspace> doesn't emit sig_show_completions
    qtbot.keyClicks(code_editor, 'math.a')
    with qtbot.waitSignal(code_editor.lsp_response_signal, timeout=30000):
        code_editor.document_did_change()

    try:
        with qtbot.waitSignal(completion.sig_show_completions,
                              timeout=5000) as sig:
            qtbot.keyPress(code_editor, Qt.Key_Tab)
            qtbot.keyPress(code_editor, Qt.Key_Backspace)
        raise RuntimeError("The signal should not have been received!")
    except pytestqt.exceptions.TimeoutError:
        pass

    try:
        with qtbot.waitSignal(completion.sig_show_completions,
                              timeout=5000) as sig:
            qtbot.keyPress(code_editor, Qt.Key_Tab)
            qtbot.keyPress(code_editor, Qt.Key_Return)
        raise RuntimeError("The signal should not have been received!")
    except pytestqt.exceptions.TimeoutError:
        pass

    assert code_editor.toPlainText() == 'import math\nmath.hypot\n'\
                                        'math.hypot()\nmath.asin\n'\
                                        'math.f\nmath.asin\n'\
                                        'math.asinangle\n'\
                                        'math.\n'
    code_editor.toggle_automatic_completions(True)
    code_editor.toggle_code_snippets(True)


@pytest.mark.slow
@pytest.mark.first
@pytest.mark.skipif(not rtree_available or PY2,
                    reason='Only works if rtree is installed')
def test_code_snippets(lsp_codeeditor, qtbot):
    assert rtree_available
    code_editor, lsp = lsp_codeeditor
    completion = code_editor.completion_widget
    snippets = code_editor.editor_extensions.get('SnippetsExtension')

    CONF.set('lsp-server', 'code_snippets', True)
    lsp.update_configuration()

    code_editor.toggle_automatic_completions(False)
    code_editor.toggle_code_snippets(True)
    # Set cursor to start
    code_editor.go_to_line(1)

    text = """
    def test_func(xlonger, y1, some_z):
        pass
    """
    text = textwrap.dedent(text)

    code_editor.insert_text(text)
    with qtbot.waitSignal(code_editor.lsp_response_signal, timeout=30000):
        code_editor.document_did_change()

    qtbot.keyPress(code_editor, Qt.Key_Enter, delay=300)
    qtbot.keyPress(code_editor, Qt.Key_Enter, delay=300)
    qtbot.keyClicks(code_editor, 'test_')
    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyPress(code_editor, Qt.Key_Tab)

    assert 'test_func(xlonger, y1, some_z)' in {
        x['label'] for x in sig.args[0]}

    expected_insert = 'test_func(${1:xlonger}, ${2:y1}, ${3:some_z})$0'
    insert = sig.args[0][0]
    assert expected_insert == insert['insertText']

    assert snippets.is_snippet_active
    assert code_editor.has_selected_text()

    # Rotate through snippet regions
    cursor = code_editor.textCursor()
    arg1 = cursor.selectedText()
    assert 'xlonger' == arg1
    assert snippets.active_snippet == 1

    qtbot.keyPress(code_editor, Qt.Key_Tab)
    cursor = code_editor.textCursor()
    arg2 = cursor.selectedText()
    assert 'y1' == arg2
    assert snippets.active_snippet == 2

    qtbot.keyPress(code_editor, Qt.Key_Tab)
    cursor = code_editor.textCursor()
    arg2 = cursor.selectedText()
    assert 'some_z' == arg2
    assert snippets.active_snippet == 3

    qtbot.keyPress(code_editor, Qt.Key_Tab)

    assert not snippets.is_snippet_active

    qtbot.keyPress(code_editor, Qt.Key_Enter, delay=300)

    qtbot.keyClicks(code_editor, 'test_')
    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyPress(code_editor, Qt.Key_Tab)

    # Replace selection
    qtbot.keyClicks(code_editor, 'arg1')
    qtbot.wait(5000)

    # Snippets are disabled when there are no more left
    for _ in range(0, 3):
        qtbot.keyPress(code_editor, Qt.Key_Tab)
    assert not snippets.is_snippet_active

    cursor = code_editor.textCursor()
    cursor.movePosition(QTextCursor.StartOfBlock)
    cursor.movePosition(QTextCursor.EndOfBlock, mode=QTextCursor.KeepAnchor)
    text1 = cursor.selectedText()
    assert text1 == 'test_func(arg1, y1, some_z)'

    qtbot.keyPress(code_editor, Qt.Key_Enter, delay=300)

    qtbot.keyClicks(code_editor, 'test_')
    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyPress(code_editor, Qt.Key_Tab)

    qtbot.keyPress(code_editor, Qt.Key_Tab)
    assert snippets.active_snippet == 2

    # Extend text from right
    qtbot.keyPress(code_editor, Qt.Key_Right, delay=300)
    qtbot.keyClicks(code_editor, '_var')

    qtbot.keyPress(code_editor, Qt.Key_Up, delay=300)
    qtbot.keyPress(code_editor, Qt.Key_Down, delay=300)

    cursor = code_editor.textCursor()
    cursor.movePosition(QTextCursor.StartOfBlock)
    cursor.movePosition(QTextCursor.EndOfBlock, mode=QTextCursor.KeepAnchor)
    text1 = cursor.selectedText()
    assert text1 == 'test_func(xlonger, y1_var, some_z)'

    cursor.movePosition(QTextCursor.EndOfBlock)
    code_editor.setTextCursor(cursor)

    qtbot.keyPress(code_editor, Qt.Key_Enter, delay=300)

    qtbot.keyClicks(code_editor, 'test_')
    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyPress(code_editor, Qt.Key_Tab)

    for _ in range(0, 2):
        qtbot.keyPress(code_editor, Qt.Key_Tab)
    assert snippets.active_snippet == 3

    # Extend text from left
    qtbot.keyPress(code_editor, Qt.Key_Left, delay=300)
    qtbot.keyClicks(code_editor, 's')

    qtbot.keyPress(code_editor, Qt.Key_Tab)

    assert not snippets.is_snippet_active

    cursor = code_editor.textCursor()
    cursor.movePosition(QTextCursor.StartOfBlock)
    cursor.movePosition(QTextCursor.EndOfBlock, mode=QTextCursor.KeepAnchor)
    text1 = cursor.selectedText()
    assert text1 == 'test_func(xlonger, y1, ssome_z)'

    qtbot.keyPress(code_editor, Qt.Key_Enter, delay=300)

    qtbot.keyClicks(code_editor, 'test_')
    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyPress(code_editor, Qt.Key_Tab)

    assert snippets.active_snippet == 1

    # Delete snippet region
    qtbot.keyPress(code_editor, Qt.Key_Left, delay=300)
    qtbot.keyPress(code_editor, Qt.Key_Backspace, delay=300)
    assert len(snippets.snippets_map) == 3

    qtbot.keyPress(code_editor, Qt.Key_Tab)
    cursor = code_editor.textCursor()
    arg1 = cursor.selectedText()
    assert 'some_z' == arg1

    # Undo action
    with qtbot.waitSignal(code_editor.sig_undo,
                          timeout=10000) as sig:
        code_editor.undo()
    assert len(snippets.snippets_map) == 4

    for _ in range(0, 2):
        qtbot.keyPress(code_editor, Qt.Key_Tab)

    cursor = code_editor.textCursor()
    arg1 = cursor.selectedText()
    assert 'some_z' == arg1

    with qtbot.waitSignal(code_editor.sig_redo,
                          timeout=10000) as sig:
        code_editor.redo()
    assert len(snippets.snippets_map) == 3

    for _ in range(0, 3):
        qtbot.keyPress(code_editor, Qt.Key_Tab)
    qtbot.keyPress(code_editor, Qt.Key_Right)

    qtbot.keyPress(code_editor, Qt.Key_Enter)
    qtbot.keyPress(code_editor, Qt.Key_Backspace)

    qtbot.keyClicks(code_editor, 'test_')
    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyPress(code_editor, Qt.Key_Tab)

    # Delete text
    qtbot.keyPress(code_editor, Qt.Key_Left, delay=300)
    qtbot.keyPress(code_editor, Qt.Key_Right, delay=300)
    qtbot.keyPress(code_editor, Qt.Key_Backspace)

    for _ in range(0, 3):
        qtbot.keyPress(code_editor, Qt.Key_Tab)

    cursor = code_editor.textCursor()
    cursor.movePosition(QTextCursor.StartOfBlock)
    cursor.movePosition(QTextCursor.EndOfBlock, mode=QTextCursor.KeepAnchor)
    text1 = cursor.selectedText()
    assert text1 == 'test_func(longer, y1, some_z)'

    CONF.set('lsp-server', 'code_snippets', False)
    lsp.update_configuration()

    code_editor.toggle_automatic_completions(True)
    code_editor.toggle_code_snippets(True)


@pytest.mark.slow
@pytest.mark.first
@flaky(max_runs=5)
def test_completion_order(lsp_codeeditor, qtbot):
    code_editor, _ = lsp_codeeditor
    completion = code_editor.completion_widget

    code_editor.toggle_automatic_completions(False)

    # Set cursor to start
    code_editor.go_to_line(1)
    qtbot.keyClicks(code_editor, 'impo')
    with qtbot.waitSignal(code_editor.lsp_response_signal, timeout=30000):
        code_editor.document_did_change()

    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyPress(code_editor, Qt.Key_Tab)

    first_completion = sig.args[0][0]
    assert first_completion['insertText'] == 'import'

    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyPress(code_editor, Qt.Key_Tab)

    qtbot.keyPress(code_editor, Qt.Key_Enter, delay=300)
    qtbot.keyClicks(code_editor, 'Impo')

    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyPress(code_editor, Qt.Key_Tab)

    first_completion = sig.args[0][0]
    assert first_completion['insertText'] == 'ImportError'


@pytest.mark.slow
@pytest.mark.first
@pytest.mark.skipif(not sys.platform.startswith('linux'),
                    reason='Only works on Linux')
@flaky(max_runs=5)
def test_fallback_completions(fallback_codeeditor, qtbot):
    code_editor, _ = fallback_codeeditor
    completion = code_editor.completion_widget

    code_editor.toggle_automatic_completions(False)
    code_editor.toggle_code_snippets(False)

    # Set cursor to start
    code_editor.go_to_line(1)

    # Add some words in comments
    qtbot.keyClicks(code_editor, '# some comment and words')
    code_editor.document_did_change()

    # Enter for new line
    qtbot.keyPress(code_editor, Qt.Key_Enter, delay=1000)
    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyClicks(code_editor, 'w')
        qtbot.keyPress(code_editor, Qt.Key_Tab, delay=300)

    assert 'words' in {x['insertText'] for x in sig.args[0]}

    # Delete 'w'
    qtbot.keyPress(code_editor, Qt.Key_Backspace)

    # Insert another word
    qtbot.keyClicks(code_editor, 'another')

    qtbot.keyPress(code_editor, Qt.Key_Enter, delay=300)
    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyClicks(code_editor, 'a')
        qtbot.keyPress(code_editor, Qt.Key_Tab, delay=300)
    word_set = {x['insertText'] for x in sig.args[0]}
    assert 'another' in word_set

    # Assert that keywords are also retrieved
    assert 'assert' in word_set

    qtbot.keyPress(code_editor, Qt.Key_Backspace)
    qtbot.keyPress(code_editor, Qt.Key_Backspace)
    qtbot.keyPress(code_editor, Qt.Key_Backspace)

    qtbot.keyPress(code_editor, Qt.Key_Enter, delay=300)
    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyClicks(code_editor, 'a')
        qtbot.keyPress(code_editor, Qt.Key_Tab, delay=300)
    word_set = {x['insertText'] for x in sig.args[0]}
    assert 'another' not in word_set

    code_editor.toggle_automatic_completions(True)
    code_editor.toggle_code_snippets(True)


@pytest.mark.slow
@pytest.mark.first
@flaky(max_runs=5)
def test_kite_textEdit_completions(mock_completions_codeeditor, qtbot):
    """Test textEdit completions such as those returned by the Kite provider.

    This mocks out the completions response, and does not test the Kite
    provider directly.
    """
    code_editor, mock_response = mock_completions_codeeditor
    completion = code_editor.completion_widget

    code_editor.toggle_automatic_completions(False)
    code_editor.toggle_code_snippets(False)

    # Set cursor to start
    code_editor.go_to_line(1)

    qtbot.keyClicks(code_editor, 'my_dict.')

    # Complete my_dict. -> my_dict["dict-key"]
    mock_response.side_effect = lambda lang, method, params: {'params': [{
        'kind': CompletionItemKind.TEXT,
        'label': '["dict-key"]',
        'textEdit': {
            'newText': '["dict-key"]',
            'range': {
                'start': 7,
                'end': 8,
            },
        },
        'filterText': '',
        'sortText': '',
        'documentation': '',
        'provider': KITE_COMPLETION,
    }]} if method == LSPRequestTypes.DOCUMENT_COMPLETION else None
    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyPress(code_editor, Qt.Key_Tab, delay=300)
    mock_response.side_effect = None

    assert '["dict-key"]' in [x['label'] for x in sig.args[0]]
    qtbot.keyPress(code_editor, Qt.Key_Enter, delay=300)
    assert code_editor.toPlainText() == 'my_dict["dict-key"]\n'

    code_editor.toggle_automatic_completions(True)
    code_editor.toggle_code_snippets(True)


if __name__ == '__main__':
    pytest.main(['test_introspection.py', '--run-slow'])

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

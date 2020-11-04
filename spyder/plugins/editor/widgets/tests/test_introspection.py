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
from spyder.plugins.completion.manager.api import (
    LSPRequestTypes, CompletionItemKind)
from spyder.plugins.completion.kite.providers.document import KITE_COMPLETION
from spyder.plugins.completion.kite.utils.status import (
    check_if_kite_installed, check_if_kite_running)
from spyder.py3compat import PY2
from spyder.config.manager import CONF


# Location of this file
LOCATION = osp.realpath(osp.join(os.getcwd(), osp.dirname(__file__)))


def set_executable_config_helper(executable=None):
    if executable is None:
        CONF.set('main_interpreter', 'default', True)
        CONF.set('main_interpreter', 'custom', False)
        CONF.set('main_interpreter', 'custom_interpreter', sys.executable)
        CONF.set('main_interpreter', 'custom_interpreters_list',
                 [sys.executable])
        CONF.set('main_interpreter', 'executable', sys.executable)
    else:
        CONF.set('main_interpreter', 'default', False)
        CONF.set('main_interpreter', 'custom', True)
        CONF.set('main_interpreter', 'custom_interpreter', executable)
        CONF.set('main_interpreter', 'custom_interpreters_list', [executable])
        CONF.set('main_interpreter', 'executable', executable)


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
@pytest.mark.skipif(bool(os.environ.get('CI', None)), reason='Fails on CI!')
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
    code_editor.set_text('')
    code_editor.completion_widget.hide()
    code_editor.go_to_line(1)

    # Complete from numpy import --> from numpy import ?
    qtbot.keyClicks(code_editor, 'from numpy import ')
    with qtbot.waitSignal(code_editor.lsp_response_signal, timeout=30000):
        code_editor.document_did_change()

    # Press tab and get completions
    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000):
        qtbot.keyPress(code_editor, Qt.Key_Tab)

    # Check the completion widget is visible
    assert completion.isHidden() is False

    # Write a random delimeter on the code editor
    delimiter = random.choice(delimiters)
    print(delimiter)
    qtbot.keyClicks(code_editor, delimiter)
    qtbot.wait(1000)

    # Check the completion widget is not visible
    assert completion.isHidden() is True

    code_editor.toggle_automatic_completions(True)
    code_editor.toggle_code_snippets(True)


@pytest.mark.slow
@pytest.mark.first
@flaky(max_runs=5)
@pytest.mark.skipif(
    os.environ.get('CI') and (PY2 and os.name != 'nt'),
    reason='Fails on CI with Mac/Linux and Python 2')
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
@pytest.mark.first
@flaky(max_runs=5)
def test_automatic_completions_tab_bug(lsp_codeeditor, qtbot):
    """
    Test on-the-fly completions.

    Autocompletions should not be invoked when Tab/Backtab is pressed.

    See: spyder-ide/spyder#11625
    """
    code_editor, _ = lsp_codeeditor
    completion = code_editor.completion_widget
    code_editor.toggle_code_snippets(False)

    code_editor.set_text('x = 1')
    code_editor.set_cursor_position('sol')

    try:
        with qtbot.waitSignal(completion.sig_show_completions,
                              timeout=5000):
            qtbot.keyPress(code_editor, Qt.Key_Tab)
        assert False
    except pytestqt.exceptions.TimeoutError:
        pass

    try:
        with qtbot.waitSignal(completion.sig_show_completions,
                              timeout=5000):
            qtbot.keyPress(code_editor, Qt.Key_Backtab)
        assert False
    except pytestqt.exceptions.TimeoutError:
        pass


@pytest.mark.slow
@pytest.mark.first
@flaky(max_runs=5)
def test_automatic_completions_space_bug(lsp_codeeditor, qtbot):
    """Test that completions are not invoked when pressing the space key."""
    code_editor, _ = lsp_codeeditor
    completion = code_editor.completion_widget
    code_editor.toggle_code_snippets(False)

    code_editor.set_text('x = 1')
    code_editor.set_cursor_position('sol')
    qtbot.keyPress(code_editor, Qt.Key_Right)

    try:
        with qtbot.waitSignal(completion.sig_show_completions,
                              timeout=5000):
            qtbot.keyPress(code_editor, Qt.Key_Space)
        assert False
    except pytestqt.exceptions.TimeoutError:
        pass


@pytest.mark.slow
@flaky(max_runs=3)
def test_automatic_completions_parens_bug(lsp_codeeditor, qtbot):
    """
    Test on-the-fly completions.

    Autocompletions for variables don't work inside function calls.
    Note: Don't mark this as first because it fails on Windows.

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

    # Complete dunder imports from _ --> import _foo/_foom
    qtbot.keyClicks(code_editor, 'from _')
    with qtbot.waitSignal(code_editor.lsp_response_signal, timeout=30000):
        code_editor.document_did_change()

    # press tab and get completions
    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyPress(code_editor, Qt.Key_Tab)
    assert "__future__" in [x['label'] for x in sig.args[0]]
    code_editor.set_text('')  # Delete line
    code_editor.go_to_line(1)

    # Complete underscore variables
    qtbot.keyClicks(code_editor, '_foo = 1;_foom = 2;_fo')
    with qtbot.waitSignal(code_editor.lsp_response_signal, timeout=30000):
        code_editor.document_did_change()

    # press tab and get completions
    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyPress(code_editor, Qt.Key_Tab)
    completions = [x['label'] for x in sig.args[0]]
    assert "_foo" in completions
    assert "_foom" in completions
    code_editor.set_text('')  # Delete line
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

    # qtbot.wait(30000)
    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyPress(code_editor, Qt.Key_Tab)

    if PY2:
        assert "hypot(x, y)" in [x['label'] for x in sig.args[0]]
    else:
        assert [x['label'] for x in sig.args[0]][0] in ["hypot(x, y)",
                                                        "hypot(*coordinates)"]

    assert code_editor.toPlainText() == 'import math\nmath.hypot'

    qtbot.keyPress(code_editor, Qt.Key_Escape)

    try:
        with qtbot.waitSignal(completion.sig_show_completions,
                              timeout=10000) as sig:
            qtbot.keyPress(code_editor, Qt.Key_Tab)
    except pytestqt.exceptions.TimeoutError:
        # This should generate a timeout error because the completion
        # prefix is the same that the completions returned by Jedi.
        # This is a regression test for spyder-ide/spyder#11600
        pass



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

    # Check math.a <tab> <backspace> <escape> do not emit sig_show_completions
    qtbot.keyClicks(code_editor, 'math.a')
    with qtbot.waitSignal(code_editor.lsp_response_signal, timeout=30000):
        code_editor.document_did_change()

    try:
        with qtbot.waitSignal(completion.sig_show_completions,
                              timeout=5000) as sig:
            qtbot.keyPress(code_editor, Qt.Key_Tab)
            qtbot.keyPress(code_editor, Qt.Key_Backspace)
            qtbot.keyPress(code_editor, Qt.Key_Escape)
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
@pytest.mark.skipif(not rtree_available or PY2 or os.name == 'nt',
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
@pytest.mark.skipif((not rtree_available
                     or not check_if_kite_installed()
                     or not check_if_kite_running()),
                    reason="Only works if rtree is installed."
                           "It's not meant to be run without kite installed "
                           "and runnning")
def test_kite_code_snippets(kite_codeeditor, qtbot):
    """
    Test kite code snippets completions without initial placeholder.

    See spyder-ide/spyder#10971
    """
    assert rtree_available
    code_editor, kite = kite_codeeditor
    completion = code_editor.completion_widget
    snippets = code_editor.editor_extensions.get('SnippetsExtension')

    CONF.set('lsp-server', 'code_snippets', True)
    CONF.set('kite', 'enable', True)
    code_editor.toggle_automatic_completions(False)
    code_editor.toggle_code_snippets(True)
    kite.update_configuration()

    # Set cursor to start
    code_editor.go_to_line(1)
    qtbot.keyClicks(code_editor, 'import numpy as np')
    qtbot.keyPress(code_editor, Qt.Key_Return)
    qtbot.keyClicks(code_editor, 'np.sin')

    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyPress(code_editor, Qt.Key_Tab)

    assert 'sin('+u'\u2026'+')' in {
        x['label'] for x in sig.args[0]}

    expected_insert = 'sin($1)$0'
    insert = sig.args[0][0]
    assert expected_insert == insert['insertText']

    # Insert completion
    qtbot.wait(500)
    qtbot.keyPress(completion, Qt.Key_Tab)
    assert snippets.is_snippet_active

    # Get code selected text
    cursor = code_editor.textCursor()
    arg1 = cursor.selectedText()
    assert '' == arg1
    assert snippets.active_snippet == 1

    code_editor.set_cursor_position('eol')
    qtbot.keyPress(code_editor, Qt.Key_Left)

    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig2:
        code_editor.do_completion()

    assert '<x>)' in {x['label'] for x in sig2.args[0]}

    expected_insert = '${1:[x]})$0'
    insert = sig2.args[0][0]
    assert expected_insert == insert['textEdit']['newText']
    qtbot.keyPress(completion, Qt.Key_Tab)

    # Snippets are disabled when there are no more left
    code_editor.set_cursor_position('eol')
    qtbot.keyPress(code_editor, Qt.Key_Enter)
    assert not snippets.is_snippet_active

    cursor = code_editor.textCursor()
    cursor.movePosition(QTextCursor.PreviousBlock)
    cursor.movePosition(QTextCursor.StartOfBlock)
    cursor.movePosition(QTextCursor.EndOfBlock, mode=QTextCursor.KeepAnchor)
    text1 = cursor.selectedText()
    assert text1 == 'np.sin([x])'

    CONF.set('lsp-server', 'code_snippets', False)
    CONF.set('kite', 'enable', False)
    kite.update_configuration()

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
@pytest.mark.skipif(not sys.platform.startswith('linux') or PY2,
                    reason='Only works on Linux and Python 3')
@flaky(max_runs=5)
def test_fallback_completions(fallback_codeeditor, qtbot):
    code_editor, _ = fallback_codeeditor
    completion = code_editor.completion_widget

    code_editor.toggle_automatic_completions(False)
    code_editor.toggle_code_snippets(False)

    # Set cursor to start
    code_editor.go_to_line(1)

    # Add some words in comments
    qtbot.keyClicks(code_editor, '# some comment and whole words')
    code_editor.document_did_change()

    # Enter for new line
    qtbot.keyPress(code_editor, Qt.Key_Enter, delay=1000)
    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyClicks(code_editor, 'wh')
        qtbot.keyPress(code_editor, Qt.Key_Tab, delay=300)

    # Assert all retrieved words start with 'wh'
    assert all({x['insertText'].startswith('wh') for x in sig.args[0]})

    # Delete 'wh'
    for _ in range(2):
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

    for _ in range(3):
        qtbot.keyPress(code_editor, Qt.Key_Backspace)

    qtbot.keyPress(code_editor, Qt.Key_Enter, delay=300)
    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyClicks(code_editor, 'a')
        qtbot.keyPress(code_editor, Qt.Key_Tab, delay=300)
    word_set = {x['insertText'] for x in sig.args[0]}
    assert 'another' not in word_set

    # Check that fallback doesn't give an error with utf-16 characters.
    # This is a regression test for issue spyder-ide/spyder#11862.
    qtbot.keyPress(code_editor, Qt.Key_Enter, delay=300)
    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        code_editor.append("'😒 foobar'")
        qtbot.keyPress(code_editor, Qt.Key_Enter, delay=300)
        qtbot.keyClicks(code_editor, 'foob')
        qtbot.keyPress(code_editor, Qt.Key_Tab, delay=300)
    word_set = {x['insertText'] for x in sig.args[0]}
    assert 'foobar' in word_set

    code_editor.toggle_automatic_completions(True)
    code_editor.toggle_code_snippets(True)


@pytest.mark.slow
@pytest.mark.first
@flaky(max_runs=5)
def test_text_snippet_completions(snippets_codeeditor, qtbot):
    code_editor, _ = snippets_codeeditor
    completion = code_editor.completion_widget

    code_editor.toggle_automatic_completions(False)
    code_editor.toggle_code_snippets(False)

    # Set cursor to start
    code_editor.go_to_line(1)

    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyClicks(code_editor, 'f')
        qtbot.keyPress(code_editor, Qt.Key_Tab, delay=300)

    # Assert all retrieved words start with 'f'
    assert all({x['sortText'][1] in {'for', 'from'} for x in sig.args[0]})

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


@pytest.mark.slow
@pytest.mark.first
@flaky(max_runs=5)
@pytest.mark.skipif(os.name == 'nt', reason='Hangs on Windows')
def test_completions_extra_paths(lsp_codeeditor, qtbot, tmpdir):
    """Exercise code completion when adding extra paths."""
    code_editor, lsp_plugin = lsp_codeeditor
    completion = code_editor.completion_widget
    code_editor.toggle_automatic_completions(False)
    code_editor.toggle_code_snippets(False)

    # Create a file to use as extra path
    temp_content = '''
def spam():
    pass
'''
    CONF.set('main', 'spyder_pythonpath', [])
    lsp_plugin.update_configuration()
    qtbot.wait(500)
    qtbot.keyClicks(code_editor, 'import foo')
    qtbot.keyPress(code_editor, Qt.Key_Enter)
    qtbot.keyClicks(code_editor, 'foo.s')
    code_editor.document_did_change()
    qtbot.keyPress(code_editor, Qt.Key_Tab)
    qtbot.wait(500)
    assert code_editor.toPlainText() == 'import foo\nfoo.s'

    p = tmpdir.mkdir("extra_path")
    extra_paths = [str(p)]
    p = p.join("foo.py")
    p.write(temp_content)

    # Set extra paths
    print(extra_paths)
    CONF.set('main', 'spyder_pythonpath', extra_paths)
    lsp_plugin.update_configuration()
    code_editor.document_did_change()
    qtbot.wait(500)

    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyPress(code_editor, Qt.Key_Tab)
    assert "spam()" in [x['label'] for x in sig.args[0]]
    assert code_editor.toPlainText() == 'import foo\nfoo.spam'

    # Reset extra paths
    CONF.set('main', 'spyder_pythonpath', [])
    lsp_plugin.update_configuration()
    qtbot.wait(500)


@pytest.mark.slow
@pytest.mark.first
@pytest.mark.skipif(os.environ.get('CI') is None,
                    reason='Run tests only on CI.')
@flaky(max_runs=5)
def test_completions_environment(lsp_codeeditor, qtbot, tmpdir):
    """Exercise code completion when adding extra paths."""
    code_editor, lsp_plugin = lsp_codeeditor
    completion = code_editor.completion_widget
    code_editor.toggle_automatic_completions(False)
    code_editor.toggle_code_snippets(False)

    # Get jedi test env
    conda_envs_path = os.path.dirname(sys.prefix)
    conda_jedi_env = os.path.join(conda_envs_path, 'jedi-test-env')

    if os.name == 'nt':
        py_exe = os.path.join(conda_jedi_env, 'python.exe')
    else:
        py_exe = os.path.join(conda_jedi_env, 'bin', 'python')

    print(sys.executable)
    print(py_exe)

    assert os.path.isfile(py_exe)

    # Set environment
    set_executable_config_helper()
    lsp_plugin.update_configuration()

    qtbot.keyClicks(code_editor, 'import flas')
    qtbot.keyPress(code_editor, Qt.Key_Tab)
    qtbot.wait(2000)
    assert code_editor.toPlainText() == 'import flas'

    # Reset extra paths
    set_executable_config_helper(py_exe)
    lsp_plugin.update_configuration()

    code_editor.set_text('')
    qtbot.keyClicks(code_editor, 'import flas')
    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyPress(code_editor, Qt.Key_Tab)

    assert "flask" in [x['label'] for x in sig.args[0]]
    assert code_editor.toPlainText() == 'import flask'

    set_executable_config_helper()
    lsp_plugin.update_configuration()


if __name__ == '__main__':
    pytest.main(['test_introspection.py', '--run-slow'])

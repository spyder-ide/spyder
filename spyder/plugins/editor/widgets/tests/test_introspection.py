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
import sys

# Third party imports
import pytest
import pytestqt

from qtpy.QtCore import Qt

# Local imports
from spyder.py3compat import PY2


# Location of this file
LOCATION = osp.realpath(osp.join(os.getcwd(), osp.dirname(__file__)))


@pytest.mark.slow
@pytest.mark.first
def test_space_completion(lsp_codeeditor, qtbot):
    """Validate completion's space character handling."""
    code_editor, _ = lsp_codeeditor
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


@pytest.mark.slow
@pytest.mark.first
def test_hide_widget_completion(lsp_codeeditor, qtbot):
    """Validate hiding completion widget after a delimeter or operator."""
    code_editor, _ = lsp_codeeditor
    completion = code_editor.completion_widget

    delimiters = ['(', ')', '[', ']', '{', '}', ',', ':', ';', '@', '=', '->',
                  '+=', '-=', '*=', '/=', '//=', '%=', '@=', '&=', '|=', '^=',
                  '>>=', '<<=', '**=']
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


@pytest.mark.slow
@pytest.mark.first
def test_completions(lsp_codeeditor, qtbot):
    """Exercise code completion in several ways."""
    code_editor, _ = lsp_codeeditor
    completion = code_editor.completion_widget

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

    # Complete math.d() -> math.degrees()
    qtbot.keyClicks(code_editor, 'math.d')
    with qtbot.waitSignal(code_editor.lsp_response_signal, timeout=30000):
        code_editor.document_did_change()

    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyPress(code_editor, Qt.Key_Tab)
    assert "degrees(x)" in [x['label'] for x in sig.args[0]]

    assert code_editor.toPlainText() == 'import math\nmath.degrees'

    # enter for new line
    qtbot.keyPress(code_editor, Qt.Key_Enter, delay=300)

    # Complete math.d() -> math.degrees()
    qtbot.keyClicks(code_editor, 'math.d(')
    qtbot.keyPress(code_editor, Qt.Key_Left, delay=300)
    qtbot.keyClicks(code_editor, 'e')
    with qtbot.waitSignal(code_editor.lsp_response_signal, timeout=30000):
        code_editor.document_did_change()

    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyPress(code_editor, Qt.Key_Tab)
    assert "degrees(x)" in [x['label'] for x in sig.args[0]]

    # right for () + enter for new line
    qtbot.keyPress(code_editor, Qt.Key_Right, delay=300)
    qtbot.keyPress(code_editor, Qt.Key_Right, delay=300)
    qtbot.keyPress(code_editor, Qt.Key_Enter, delay=300)

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
    assert "asin" == completion.item(0).text()
    qtbot.keyPress(completion, Qt.Key_Enter, delay=300)

    # enter for new line
    qtbot.keyPress(code_editor, Qt.Key_Enter, delay=300)

    # Check can get list back
    qtbot.keyClicks(code_editor, 'math.c')
    with qtbot.waitSignal(code_editor.lsp_response_signal, timeout=30000):
        code_editor.document_did_change()

    with qtbot.waitSignal(completion.sig_show_completions,
                          timeout=10000) as sig:
        qtbot.keyPress(code_editor, Qt.Key_Tab)
    assert completion.count() == 4
    assert "ceil(x)" in [x['label'] for x in sig.args[0]]
    qtbot.keyClicks(completion, 'e')
    assert completion.count() == 1
    qtbot.keyPress(completion, Qt.Key_Backspace)
    assert completion.count() == 4

    # enter for new line
    qtbot.keyPress(code_editor, Qt.Key_Enter, delay=300)

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

    # Check math.a <tab> <backspace> doesn't emit sig_show_completions
    qtbot.keyPress(code_editor, Qt.Key_Enter, delay=300)
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

    assert code_editor.toPlainText() == 'import math\nmath.degrees\n'\
                                        'math.degrees()\nmath.asin\n'\
                                        'math.c\nmath.asin\n'\
                                        'math.asinangle\n'\
                                        'math.\n'


@pytest.mark.slow
@pytest.mark.first
@pytest.mark.skipif(not sys.platform.startswith('linux'),
                    reason='Only works on Linux')
def test_fallback_completions(fallback_codeeditor, qtbot):
    code_editor, _ = fallback_codeeditor
    completion = code_editor.completion_widget

    # Set cursor to start
    code_editor.go_to_line(1)

    # Add some words in comments
    qtbot.keyClicks(code_editor, '# some comment and words')
    code_editor.document_did_change()

    # Enter for new line
    qtbot.keyPress(code_editor, Qt.Key_Enter, delay=300)
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

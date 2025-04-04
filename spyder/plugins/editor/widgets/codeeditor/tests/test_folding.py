# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""Tests for the folding features."""

# Standard library imports
import sys

# Third party imports
from flaky import flaky
import pytest
import pytestqt
from qtpy.QtCore import Qt
from qtpy.QtGui import QTextCursor

# Local imports
from spyder.config.base import running_in_ci


# ---- Code to test
# -----------------------------------------------------------------------------
text = """
def myfunc2():
    x = [0, 1, 2, 3,
        3 , 4] # Arbitary Code
    x[0] = 2 # Desired break
    print(x[1]) # Arbitary Code
# don't delete this comment
responses = {
    100: ('Continue', 'Request received, please continue'),
    101: ('Switching Protocols','Switching to new protocol'),
    200: ('OK', 'Request fulfilled, document follows'),
    201: ('Created', 'Document created, URL follows'),
    202: ('Accepted','Request accepted, processing continues off-line'),
    203: ('Non-Authoritative Information', 'Request fulfilled from cache'),
    204: ('No Content', 'Request fulfilled, nothing follows'),
    205: ('Reset Content', 'Clear input form for further input.'),
    206: ('Partial Content', 'Partial content follows.'),
    300: ('Multiple Choices','Object has several resources'),
    301: ('Moved Permanently', 'Object moved permanently -- see URI list'),
    302: ('Found', 'Object moved temporarily -- see URI list'),
    303: ('See Other', 'Object moved -- see Method and URL list'),
    304: ('Not Modified',
        'Document has not changed since given time'),
    305: ('Use Proxy',
        'You must use proxy specified in Location to access this ',
        'resource.'),
    307: ('Temporary Redirect',
        'Object moved temporarily -- see URI list'),

    400: ('Bad Request',
        'Bad request syntax or unsupported method'),
    401: ('Unauthorized',
        'No permission -- see authorization schemes'),
    402: ('Payment Required',
        'No payment -- see charging schemes')
}"""


# ---- Tests
# -----------------------------------------------------------------------------
@pytest.mark.order(2)
@flaky(max_runs=5)
def test_folding(completions_codeeditor, qtbot):
    code_editor, __ = completions_codeeditor
    code_editor.toggle_code_folding(True)
    code_editor.insert_text(text)
    folding_panel = code_editor.panels.get('FoldingPanel')

    # Wait for the update thread to finish
    qtbot.waitSignal(code_editor.update_folding_thread.finished)
    qtbot.waitUntil(lambda: code_editor.folding_in_sync)

    folding_regions = folding_panel.folding_regions
    folding_levels = folding_panel.folding_levels

    expected_regions = {2: 6, 3: 4, 8: 36, 22: 23, 24: 26, 27: 28,
                        30: 31, 32: 33, 34: 35}
    expected_levels = {2: 0, 3: 1, 8: 0, 22: 1, 24: 1, 27: 1, 30: 1,
                       32: 1, 34: 1}
    assert folding_regions == expected_regions
    assert expected_levels == folding_levels
    code_editor.toggle_code_folding(False)


@pytest.mark.order(2)
@flaky(max_runs=5)
def test_unfold_when_searching(search_codeeditor, qtbot):
    editor, finder = search_codeeditor
    editor.toggle_code_folding(True)

    folding_panel = editor.panels.get('FoldingPanel')
    editor.insert_text(text)

    # Wait for the update thread to finish
    qtbot.waitSignal(editor.update_folding_thread.finished)
    qtbot.waitUntil(lambda: editor.folding_in_sync)

    line_search = editor.document().findBlockByLineNumber(3)

    # fold region
    block = editor.document().findBlockByLineNumber(2)
    folding_panel.toggle_fold_trigger(block)
    assert not line_search.isVisible()

    # unfolded when searching
    finder.show()
    qtbot.keyClicks(finder.search_text, 'print')
    qtbot.keyPress(finder.search_text, Qt.Key_Return)
    assert line_search.isVisible()
    editor.toggle_code_folding(False)


@pytest.mark.order(2)
@flaky(max_runs=5)
def test_unfold_goto(completions_codeeditor, qtbot):
    editor, __ = completions_codeeditor
    editor.toggle_code_folding(True)
    editor.insert_text(text)
    folding_panel = editor.panels.get('FoldingPanel')

    # Wait for the update thread to finish
    qtbot.waitSignal(editor.update_folding_thread.finished)
    qtbot.waitUntil(lambda: editor.folding_in_sync)

    line_goto = editor.document().findBlockByLineNumber(5)

    # fold region
    block = editor.document().findBlockByLineNumber(2)
    folding_panel.toggle_fold_trigger(block)
    assert not line_goto.isVisible()

    # unfolded when goto
    editor.go_to_line(6)
    assert line_goto.isVisible()
    editor.toggle_code_folding(False)


@flaky(max_runs=5)
@pytest.mark.order(2)
@pytest.mark.skipif(
    running_in_ci() and sys.platform.startswith("linux"),
    reason="Fails on Linux and CIs"
)
def test_delete_folded_line(completions_codeeditor, qtbot):
    editor, __ = completions_codeeditor
    editor.toggle_code_folding(True)
    editor.insert_text(text)
    folding_panel = editor.panels.get('FoldingPanel')

    def fold_and_delete_region(key):
        # Wait for the update thread to finish
        qtbot.waitSignal(editor.update_folding_thread.finished)
        qtbot.waitUntil(lambda: editor.folding_in_sync)

        # fold region
        folded_line = editor.document().findBlockByLineNumber(5)
        folding_panel.toggle_fold_trigger(
            editor.document().findBlockByLineNumber(2)
        )
        qtbot.waitUntil(lambda: folding_panel.folding_status.get(2))
        assert not folded_line.isVisible()

        editor.go_to_line(2)
        if key == Qt.Key_Delete:
            move = QTextCursor.MoveAnchor
        else:
            move = QTextCursor.KeepAnchor
        editor.moveCursor(QTextCursor.NextCharacter, move)

        # Press Delete or Backspace in folded line
        qtbot.keyPress(editor, key)

    # Remove folded line with Delete key
    fold_and_delete_region(Qt.Key_Delete)

    # Check entire folded region was removed
    assert "myfunc2" not in editor.toPlainText()
    assert "print" not in editor.toPlainText()
    assert editor.blockCount() == 31

    # Check line after folded region was not removed
    assert "# don't delete this comment" in editor.toPlainText()

    # Press Ctrl+Z
    qtbot.keyClick(editor, Qt.Key_Z, Qt.ControlModifier)

    # Remove folded line with Backspace key
    fold_and_delete_region(Qt.Key_Backspace)

    # Check entire folded region was removed
    assert "myfunc2" not in editor.toPlainText()
    assert "print" not in editor.toPlainText()
    assert editor.blockCount() == 31

    # Check line after folded region was not removed
    assert "# don't delete this comment" in editor.toPlainText()

    # Press Ctrl+Z again
    qtbot.keyClick(editor, Qt.Key_Z, Qt.ControlModifier)

    # Wait for the update thread to finish
    qtbot.waitSignal(editor.update_folding_thread.finished)
    qtbot.waitUntil(lambda: editor.folding_in_sync)

    # Check the folded region was restored
    assert "myfunc2" in editor.toPlainText()
    assert "print" in editor.toPlainText()
    assert editor.blockCount() == 36

    # Check first folding was computed correctly again
    assert folding_panel.folding_regions.get(2) == 6

    editor.toggle_code_folding(False)


@flaky(max_runs=5)
@pytest.mark.order(2)
@pytest.mark.skipif(
    running_in_ci() and sys.platform.startswith("linux"),
    reason="Fails on Linux and CIs"
)
def test_delete_selections_with_folded_lines(completions_codeeditor, qtbot):
    editor, __ = completions_codeeditor
    editor.toggle_code_folding(True)
    editor.insert_text(text)
    folding_panel = editor.panels.get('FoldingPanel')

    def remove_selection_with_fold_line(start_line, nlines_to_select):
        # Wait for the update thread to finish
        qtbot.waitSignal(editor.update_folding_thread.finished)
        qtbot.waitUntil(lambda: editor.folding_in_sync)

        # fold region
        folded_line = editor.document().findBlockByLineNumber(5)
        folding_panel.toggle_fold_trigger(
            editor.document().findBlockByLineNumber(2)
        )
        qtbot.waitUntil(lambda: folding_panel.folding_status.get(2))
        assert not folded_line.isVisible()

        # Create a selection
        editor.go_to_line(start_line)

        visible_lines = 0
        for i in range(editor.blockCount()):
            if i < start_line:
                continue
            editor.moveCursor(QTextCursor.NextBlock, QTextCursor.KeepAnchor)
            if editor.textCursor().block().isVisible():
                visible_lines += 1
            if visible_lines == nlines_to_select:
                break

        editor.moveCursor(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)

        # Press Delete key
        qtbot.keyPress(editor, Qt.Key_Delete)

    def restore_initial_state():
        # Press Ctrl+Z
        qtbot.keyClick(editor, Qt.Key_Z, Qt.ControlModifier)

        # Wait for the update thread to finish
        qtbot.waitSignal(editor.update_folding_thread.finished)
        qtbot.waitUntil(lambda: editor.folding_in_sync)

        # Check the folded region was restored
        assert "myfunc2" in editor.toPlainText()
        assert editor.blockCount() == 36

    # Remove a selection that ends in the folded region
    remove_selection_with_fold_line(start_line=1, nlines_to_select=1)

    # Check folded region was removed
    assert "print" not in editor.toPlainText()
    assert editor.blockCount() == 30

    restore_initial_state()

    # Remove a selection that starts wtih the folded region
    remove_selection_with_fold_line(start_line=2, nlines_to_select=2)

    # Check folded region was removed
    assert "print" not in editor.toPlainText()
    assert "responses" not in editor.toPlainText()
    assert editor.blockCount() == 30

    restore_initial_state()

    # Remove a selection that has a folded region in the middle
    remove_selection_with_fold_line(start_line=1, nlines_to_select=4)

    # Check folded region was removed
    assert "print" not in editor.toPlainText()
    assert "responses" not in editor.toPlainText()
    assert "100" not in editor.toPlainText()
    assert editor.blockCount() == 28

    editor.toggle_code_folding(False)


@flaky(max_runs=5)
@pytest.mark.order(2)
def test_preserve_folded_regions_after_paste(completions_codeeditor, qtbot):
    editor, __ = completions_codeeditor
    editor.toggle_code_folding(True)
    editor.insert_text(text)
    folding_panel = editor.panels.get('FoldingPanel')

    def copy_region(start_line, nlines_to_select):
        editor.go_to_line(start_line)
        for __ in range(nlines_to_select):
            editor.moveCursor(QTextCursor.NextBlock, QTextCursor.KeepAnchor)
        editor.moveCursor(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
        editor.copy()

    def paste_region(start_line, nenters, paste_line=None):
        editor.go_to_line(start_line)
        for __ in range(nenters):
            qtbot.keyPress(editor, Qt.Key_Return)
        if paste_line:
            editor.go_to_line(paste_line)
        editor.paste()

    # Wait for the update thread to finish
    qtbot.waitSignal(editor.update_folding_thread.finished)
    qtbot.waitUntil(lambda: editor.folding_in_sync)

    # Fold last region
    folding_panel.toggle_fold_trigger(
        editor.document().findBlockByLineNumber(34)
    )
    assert folding_panel.folding_status[34]

    # First region to copy/paste (code has a syntax error).
    copy_region(start_line=7, nlines_to_select=13)
    paste_region(start_line=7, nenters=2, paste_line=8)

    # Check folding was preserved
    editor.go_to_line(49)
    qtbot.waitUntil(lambda: folding_panel.folding_status.get(49))

    # Second region to copy/paste
    copy_region(start_line=10, nlines_to_select=12)
    paste_region(start_line=22, nenters=1, paste_line=22)

    # Make the code syntactically correct
    qtbot.keyClicks(editor, "}")

    # Check folding decos are not updated out of the visible buffer
    with pytest.raises(pytestqt.exceptions.TimeoutError):
        qtbot.waitUntil(
            lambda: folding_panel.folding_status.get(62),
            timeout=3000
        )

    # Show expected folded line to get folding updated.
    editor.go_to_line(62)

    # Check folding was preserved
    qtbot.waitUntil(lambda: folding_panel.folding_status.get(62))

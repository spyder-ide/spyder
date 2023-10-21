# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""Tests for code formatting using Editor/EditorStack instances."""

# Standard library imports
import random

# Third party imports
from flaky import flaky
import pytest
from qtpy.QtCore import Qt
from qtpy.QtGui import QTextCursor
from qtpy.QtWidgets import QMessageBox

# Local imports
from spyder.config.manager import CONF
from spyder.plugins.editor.widgets.codeeditor.tests.conftest import (
    autopep8,
    black,
    get_formatter_values
)


# ---- Tests
@pytest.mark.order(1)
@pytest.mark.parametrize('formatter', [autopep8, black])
def test_closing_document_formatting(
        formatter, completions_editor, qtbot, monkeypatch):
    """Check that auto-formatting works when closing an usaved file."""
    file_path, editorstack, code_editor, completion_plugin = completions_editor
    text, expected = get_formatter_values(formatter, newline='\n')

    # Set formatter
    editorstack.set_format_on_save(True)
    CONF.set(
        'completions',
        ('provider_configuration', 'lsp', 'values', 'formatting'),
        formatter
    )

    with qtbot.waitSignal(completion_plugin.sig_editor_rpc):
        completion_plugin.after_configuration_update([])
    qtbot.wait(2000)

    # Set text in editor
    code_editor.set_text(text)

    # Notify changes
    with qtbot.waitSignal(
            code_editor.completions_response_signal, timeout=30000):
        code_editor.document_did_change()

    # Perform formatting while closing the file
    with qtbot.waitSignal(
            code_editor.completions_response_signal, timeout=30000):
        monkeypatch.setattr(QMessageBox, 'exec_',
                            classmethod(lambda *args: QMessageBox.Yes))
        monkeypatch.setattr(editorstack, 'select_savename',
                            lambda *args: str(file_path))
        editorstack.save_dialog_on_tests = True
        editorstack.close_file()

    # Load again formatted file and check content
    code_editor = editorstack.load(str(file_path)).editor

    assert code_editor.get_text_with_eol() == expected


@flaky(max_runs=20)
@pytest.mark.order(1)
@pytest.mark.parametrize('formatter', [autopep8, black])
def test_formatting_on_save(completions_editor, formatter, qtbot):
    """
    Check that auto-formatting on save works as expected and that we restore
    the current line after doing it.

    This includes a regression test for issue spyder-ide/spyder#19958
    """
    file_path, editorstack, code_editor, completion_plugin = completions_editor
    text, expected = get_formatter_values(formatter, newline='\n')

    # Set formatter
    editorstack.set_format_on_save(True)
    CONF.set(
        'completions',
        ('provider_configuration', 'lsp', 'values', 'formatting'),
        formatter
    )

    with qtbot.waitSignal(completion_plugin.sig_editor_rpc):
        completion_plugin.after_configuration_update([])
    qtbot.wait(2000)

    # Set text in editor
    code_editor.set_text(text)

    # Notify changes
    with qtbot.waitSignal(
            code_editor.completions_response_signal, timeout=30000):
        code_editor.document_did_change()

    # Set a random current line
    current_line = random.randint(0, code_editor.blockCount())
    code_editor.moveCursor(QTextCursor.Start)
    cursor = code_editor.textCursor()
    cursor.movePosition(QTextCursor.Down, QTextCursor.MoveAnchor, current_line)
    code_editor.setTextCursor(cursor)
    qtbot.wait(500)

    # Make a simple change to the file
    code_editor.moveCursor(QTextCursor.EndOfLine)
    qtbot.keyPress(code_editor, Qt.Key_Space)
    current_position = cursor.position()
    qtbot.wait(500)

    # Save the file
    with qtbot.waitSignal(
            code_editor.completions_response_signal, timeout=30000):
        editorstack.save(force=True)
    qtbot.wait(1000)

    # Check that auto-formatting was applied on save and that we restored the
    # previous line.
    assert code_editor.get_text_with_eol() == expected
    assert code_editor.textCursor().position() == current_position

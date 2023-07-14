# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""Tests for code formatting."""

# Standard library imports
import os
import os.path as osp
import random

# Third party imports
from flaky import flaky
import pytest
from qtpy.QtCore import Qt
from qtpy.QtGui import QTextCursor
from qtpy.QtWidgets import QMessageBox
import yapf

# Local imports
from spyder.config.manager import CONF
from spyder.utils.programs import is_module_installed


# ---- Auxiliary constants and functions
HERE = osp.dirname(osp.abspath(__file__))
ASSETS = osp.join(HERE, 'assets')


autopep8 = pytest.param(
    'autopep8',
    marks=pytest.mark.skipif(
        os.name == 'nt',
        reason='autopep8 produces a different output on Windows'
    )
)

yapf = pytest.param(
    'yapf',
    marks=pytest.mark.skipif(
        is_module_installed('yapf', '<0.32.0'),
        reason='Versions older than 0.32 produce different outputs'
    )
)

black = pytest.param(
    'black',
    marks=pytest.mark.skipif(
        is_module_installed('python-lsp-black', '<1.2.0'),
        reason="Versions older than 1.2 don't handle eol's correctly"
    )
)


def get_formatter_values(formatter, newline, range_fmt=False, max_line=False):
    if range_fmt:
        suffix = 'range'
    elif max_line:
        suffix = 'max_line'
    else:
        suffix = 'result'

    original_file = osp.join(ASSETS, 'original_file.py')
    formatted_file = osp.join(ASSETS, '{0}_{1}.py'.format(formatter, suffix))

    with open(original_file, 'r') as f:
        text = f.read()
    text = text.replace('\n', newline)

    with open(formatted_file, 'r') as f:
        result = f.read()
    result = result.replace('\n', newline)

    return text, result


# ---- Tests
@pytest.mark.order(1)
@pytest.mark.parametrize('formatter', [autopep8, yapf, black])
@pytest.mark.parametrize('newline', ['\r\n', '\r', '\n'])
def test_document_formatting(formatter, newline, completions_codeeditor,
                             qtbot):
    """Validate text autoformatting via autopep8, yapf or black."""
    code_editor, completion_plugin = completions_codeeditor
    text, expected = get_formatter_values(formatter, newline)

    # Set formatter
    CONF.set(
        'completions',
        ('provider_configuration', 'lsp', 'values', 'formatting'),
        formatter
    )
    completion_plugin.after_configuration_update([])
    qtbot.wait(2000)

    # Set text in editor
    code_editor.set_text(text)

    # Assert eols are the expected ones
    assert code_editor.get_line_separator() == newline

    # Notify changes
    with qtbot.waitSignal(
            code_editor.completions_response_signal, timeout=30000):
        code_editor.document_did_change()

    # Perform formatting
    with qtbot.waitSignal(
            code_editor.completions_response_signal, timeout=30000):
        code_editor.format_document()

    # Wait for text to be formatted
    qtbot.wait(2000)

    assert code_editor.get_text_with_eol() == expected


@pytest.mark.order(1)
@pytest.mark.parametrize('formatter', [autopep8, yapf, black])
@pytest.mark.parametrize('newline', ['\r\n', '\r', '\n'])
def test_document_range_formatting(formatter, newline, completions_codeeditor,
                                   qtbot):
    """Validate text range autoformatting."""
    code_editor, completion_plugin = completions_codeeditor
    text, expected = get_formatter_values(formatter, newline, range_fmt=True)

    # This is broken in PyLSP 1.5.0. We need to investigate why.
    if formatter == 'yapf':
        return

    # Set formatter
    CONF.set(
        'completions',
        ('provider_configuration', 'lsp', 'values', 'formatting'),
        formatter
    )
    completion_plugin.after_configuration_update([])
    qtbot.wait(2000)

    # Set text in editor
    code_editor.set_text(text)

    # Assert eols are the expected ones
    assert code_editor.get_line_separator() == newline

    # Notify changes
    with qtbot.waitSignal(
            code_editor.completions_response_signal, timeout=30000):
        code_editor.document_did_change()

    # Select region to format
    code_editor.go_to_line(12)
    cursor = code_editor.textCursor()
    start = code_editor.get_position_line_number(11, -1)
    end = code_editor.get_position_line_number(27, 0)
    cursor.setPosition(start)
    cursor.setPosition(end, QTextCursor.KeepAnchor)
    cursor.movePosition(QTextCursor.EndOfBlock,
                        QTextCursor.KeepAnchor)
    code_editor.setTextCursor(cursor)

    # Perform formatting
    with qtbot.waitSignal(
            code_editor.completions_response_signal, timeout=30000):
        code_editor.format_document_range()

    # Wait to text to be formatted
    qtbot.wait(2000)
    assert code_editor.get_text_with_eol() == expected


@pytest.mark.order(1)
@pytest.mark.parametrize('formatter', [autopep8, black])
def test_max_line_length(formatter, completions_codeeditor, qtbot):
    """Validate autoformatting with a different value of max_line_length."""
    code_editor, completion_plugin = completions_codeeditor
    text, expected = get_formatter_values(
        formatter, newline='\n', max_line=True)
    max_line_length = 20

    # Set formatter and max line length options
    CONF.set(
        'completions',
        ('provider_configuration', 'lsp', 'values', 'formatting'),
        formatter
    )
    CONF.set(
        'completions',
        ('provider_configuration', 'lsp', 'values',
         'pycodestyle/max_line_length'),
        max_line_length
    )
    completion_plugin.after_configuration_update([])
    qtbot.wait(2000)

    # Set text in editor
    code_editor.set_text(text)

    # Notify changes
    with qtbot.waitSignal(
            code_editor.completions_response_signal, timeout=30000):
        code_editor.document_did_change()

    # Perform formatting
    with qtbot.waitSignal(
            code_editor.completions_response_signal, timeout=30000):
        code_editor.format_document()

    # Wait for text to be formatted
    qtbot.wait(2000)

    assert code_editor.get_text_with_eol() == expected


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

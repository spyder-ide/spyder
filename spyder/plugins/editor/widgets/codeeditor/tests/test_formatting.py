# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""Tests for code formatting using CodeEditor instances."""

# Third party imports
import pytest
from qtpy.QtGui import QTextCursor

# Local imports
from spyder.config.manager import CONF
from spyder.plugins.editor.widgets.codeeditor.tests.conftest import (
    autopep8,
    black,
    yapf,
    get_formatter_values
)


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

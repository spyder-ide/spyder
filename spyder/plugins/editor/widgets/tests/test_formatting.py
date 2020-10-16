# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""Tests for code formatting."""

# Standard library imports
import os.path as osp

# Third party imports
import pytest

# Qt imports
from qtpy.QtGui import QTextCursor

# Local imports
from spyder.config.manager import CONF


HERE = osp.dirname(osp.abspath(__file__))
ASSETS = osp.join(HERE, 'assets')


def get_formatter_values(formatter, range_fmt=False):
    suffix = 'range' if range_fmt else 'result'
    original_file = osp.join(ASSETS, 'original_file.py')
    formatted_file = osp.join(ASSETS, '{0}_{1}.py'.format(formatter, suffix))

    with open(original_file, 'r') as f:
        text = f.read()

    with open(formatted_file, 'r') as f:
        result = f.read()

    return text, result


@pytest.mark.slow
@pytest.mark.first
@pytest.mark.parametrize('formatter', ['autopep8', 'yapf', 'black'])
def test_document_formatting(formatter, lsp_codeeditor, qtbot):
    """Validate text autoformatting via autopep8, yapf or black."""
    code_editor, manager = lsp_codeeditor
    text, expected = get_formatter_values(formatter)

    # After this call the manager needs to be reinitialized
    CONF.set('lsp-server', 'formatting', formatter)
    qtbot.wait(2000)

    manager.update_configuration()
    # Set text in editor
    code_editor.set_text(text)

    # Notify changes
    with qtbot.waitSignal(code_editor.lsp_response_signal, timeout=30000):
        code_editor.document_did_change()

    # Perform formatting
    with qtbot.waitSignal(code_editor.lsp_response_signal, timeout=30000):
        code_editor.format_document()

    # Wait to text to be formatted
    qtbot.wait(2000)

    assert code_editor.toPlainText() == expected


@pytest.mark.slow
@pytest.mark.first
@pytest.mark.parametrize('formatter', ['autopep8', 'yapf', 'black'])
def test_document_range_formatting(formatter, lsp_codeeditor, qtbot):
    """Validate text range autoformatting."""
    code_editor, manager = lsp_codeeditor
    text, expected = get_formatter_values(formatter, range_fmt=True)

    # After this call the manager needs to be reinitialized
    CONF.set('lsp-server', 'formatting', formatter)
    qtbot.wait(2000)

    manager.update_configuration()
    # Set text in editor
    code_editor.set_text(text)

    # Notify changes
    with qtbot.waitSignal(code_editor.lsp_response_signal, timeout=30000):
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
    with qtbot.waitSignal(code_editor.lsp_response_signal, timeout=30000):
        code_editor.format_document_range()

    # Wait to text to be formatted
    qtbot.wait(2000)
    assert code_editor.toPlainText() == expected

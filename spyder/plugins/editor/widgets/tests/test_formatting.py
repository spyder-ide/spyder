# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""Tests for code formatting."""

# Standard library imports
import os
import os.path as osp

# Third party imports
import pytest
import yapf

# Qt imports
from qtpy.QtGui import QTextCursor

# Local imports
from spyder.config.manager import CONF
from spyder.utils.programs import is_module_installed


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


def get_formatter_values(formatter, newline, range_fmt=False):
    suffix = 'range' if range_fmt else 'result'
    original_file = osp.join(ASSETS, 'original_file.py')
    formatted_file = osp.join(ASSETS, '{0}_{1}.py'.format(formatter, suffix))

    with open(original_file, 'r') as f:
        text = f.read()
    text = text.replace('\n', newline)

    with open(formatted_file, 'r') as f:
        result = f.read()
    result = result.replace('\n', newline)

    return text, result


@pytest.mark.slow
@pytest.mark.order(1)
@pytest.mark.parametrize('formatter', [autopep8, yapf, black])
@pytest.mark.parametrize('newline', ['\r\n', '\r', '\n'])
def test_document_formatting(formatter, newline, completions_codeeditor,
                             qtbot):
    """Validate text autoformatting via autopep8, yapf or black."""
    code_editor, completion_plugin = completions_codeeditor
    text, expected = get_formatter_values(formatter, newline)

    # After this call the manager needs to be reinitialized
    CONF.set('completions',
             ('provider_configuration', 'lsp', 'values','formatting'),
             formatter)
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


@pytest.mark.slow
@pytest.mark.order(1)
@pytest.mark.parametrize('formatter', [autopep8, yapf, black])
@pytest.mark.parametrize('newline', ['\r\n', '\r', '\n'])
def test_document_range_formatting(formatter, newline, completions_codeeditor,
                                   qtbot):
    """Validate text range autoformatting."""
    code_editor, completion_plugin = completions_codeeditor
    text, expected = get_formatter_values(formatter, newline, range_fmt=True)

    # After this call the manager needs to be reinitialized
    CONF.set('completions',
             ('provider_configuration', 'lsp', 'values','formatting'),
             formatter)
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

# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#
'''
Tests for close quotes.
'''

# Third party imports
import pytest

# Local imports
from spyder.utils.qthelpers import qapplication
from spyder.widgets.sourcecode.codeeditor import CodeEditor
from spyder.utils.editor import TextHelper


# --- Fixtures
# -----------------------------------------------------------------------------
@pytest.fixture
def editor_close_quotes():
    app = qapplication()
    editor = CodeEditor(parent=None)
    kwargs = {}
    kwargs['language'] = 'Python'
    kwargs['close_quotes'] = True
    editor.setup_editor(**kwargs)
    return editor

# --- Tests
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    'text, expected_text, cursor_column',
    [
        ('"', '""', 1),  # Complete single quotes
        ("'", "''", 1),
        ('#"', '#"', 2),  # In comment, dont add extra quote
        ("#'", "#'", 2),
        ('"""', '"""', 3),  # Three quotes, dont add extra quotes
        ("'''", "'''", 3),
        ('""""', '""""""', 3),  # Four, complete docstring quotes
        ("''''", "''''''", 3),
        ('"some_string"', '"some_string"', 13),  # Write a string
        ("'some_string'", "'some_string'", 13),
    ])
def test_close_quotes(qtbot, editor_close_quotes, text, expected_text,
                      cursor_column):
    """"""
    editor = editor_close_quotes

    qtbot.keyClicks(editor, text)
    assert editor.toPlainText() == expected_text

    assert cursor_column == TextHelper(editor).current_column_nbr()


if __name__ == '__main__':
    pytest.main()

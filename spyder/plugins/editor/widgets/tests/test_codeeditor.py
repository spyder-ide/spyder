# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

# Third party imports
from qtpy.QtCore import Qt, QEvent
from qtpy.QtGui import QFont, QTextCursor, QMouseEvent
from pytestqt import qtbot
import pytest

# Local imports
from spyder.plugins.editor.widgets.editor import codeeditor
from spyder.py3compat import PY3


# --- Fixtures
# -----------------------------------------------------------------------------
@pytest.fixture
def editorbot(qtbot):
    widget = codeeditor.CodeEditor(None)
    widget.setup_editor(linenumbers=True, markers=True, tab_mode=False,
                        font=QFont("Courier New", 10),
                        show_blanks=True, color_scheme='Zenburn',
                        scroll_past_end=True)
    widget.setup_editor(language='Python')
    qtbot.addWidget(widget)
    widget.show()
    return qtbot, widget

# --- Tests
# -----------------------------------------------------------------------------
# testing lowercase transformation functionality

def test_editor_upper_to_lower(editorbot):
    qtbot, widget = editorbot
    text = 'UPPERCASE'
    widget.set_text(text)
    cursor = widget.textCursor()
    cursor.movePosition(QTextCursor.NextCharacter,
                        QTextCursor.KeepAnchor)
    widget.setTextCursor(cursor)
    widget.transform_to_lowercase()
    new_text = widget.get_text('sof', 'eof')
    assert text != new_text


def test_editor_lower_to_upper(editorbot):
    qtbot, widget = editorbot
    text = 'uppercase'
    widget.set_text(text)
    cursor = widget.textCursor()
    cursor.movePosition(QTextCursor.NextCharacter,
                        QTextCursor.KeepAnchor)
    widget.setTextCursor(cursor)
    widget.transform_to_uppercase()
    new_text = widget.get_text('sof', 'eof')
    assert text != new_text


@pytest.mark.skipif(PY3, reason='Test only makes sense on Python 2.')
def test_editor_log_lsp_handle_errors(editorbot, capsys):
    """Test the lsp error handling / dialog report Python 2."""
    qtbot, widget = editorbot
    params = {
        'params': {
            'activeParameter': 'boo',
            'signatures': {
                'documentation': b'\x81',
                'label': 'foo',
                'parameters': {
                    'boo': {
                        'documentation': b'\x81',
                        'label': 'foo',
                    },
                }
            }
        }
    }

    widget.process_signatures(params)
    captured = capsys.readouterr()
    test_1 = "Error when processing signature" in captured.err
    test_2 = "codec can't decode byte 0x81" in captured.err
    assert test_1 or test_2


@pytest.mark.parametrize(
    "input_text, expected_text, keys, strip_all",
    [
        ("for i in range(2): ",
         "for i in range(2): \n\n     \n    ",
         [Qt.Key_Enter, Qt.Key_Enter, ' ', Qt.Key_Enter],
         False),
        ('for i in range(2): ',
         'for i in range(2):\n\n    ',
         [Qt.Key_Enter, Qt.Key_Enter],
         True),
        ('myvar = 2 ',
         'myvar = 2\n',
         [Qt.Key_Enter],
         True),
        ('somecode = 1\nmyvar = 2 \nmyvar = 3',
         'somecode = 1\nmyvar = 2 \nmyvar = 3',
         [' ', Qt.Key_Up, Qt.Key_Up],
         True),
        ('somecode = 1\nmyvar = 2 ',
         'somecode = 1\nmyvar = 2 ',
         [Qt.Key_Left],
         True),
        ('"""This is a string with important spaces\n    ',
         '"""This is a string with important spaces\n    \n',
         [Qt.Key_Enter],
         True),
        ('"""string   ',
         '"""string   \n',
         [Qt.Key_Enter],
         True),
        ('somecode = 1\nmyvar = 2',
         'somecode = 1\nmyvar = 2',
         [' ', (Qt.LeftButton, 0)],
         True),
        ('somecode = 1\nmyvar = 2',
         'somecode = 1\nmyvar = 2 ',
         [' ', (Qt.LeftButton, 23)],
         True),
        ('a=1\na=2 \na=3',
         'a=1\na=2 \na=3',
         [(Qt.LeftButton, 6), Qt.Key_Up],
         True),
    ])
def test_editor_rstrip_keypress(
        editorbot, input_text, expected_text, keys, strip_all):
    """
    Test that whitespace is removed when leaving a line.
    """
    qtbot, widget = editorbot
    widget.strip_trailing_spaces_on_modify = strip_all
    widget.set_text(input_text)
    cursor = widget.textCursor()
    cursor.movePosition(QTextCursor.End)
    widget.setTextCursor(cursor)
    for key in keys:
        if isinstance(key, tuple):
            # Mouse event
            button, position = key
            cursor = widget.textCursor()
            cursor.setPosition(position)
            xypos = widget.cursorRect(cursor).center()
            widget.mousePressEvent(QMouseEvent(
                    QEvent.MouseButtonPress, xypos,
                    button, button,
                    Qt.NoModifier))
        else:
            qtbot.keyPress(widget, key)
    assert widget.toPlainText() == expected_text


@pytest.mark.parametrize(
    "input_text, expected_state", [
        ("'string ", [True, False]),
        ('"string ', [True, False]),
        ("'string \\", [True, True]),
        ('"string \\', [True, True]),
        ("'string \\ ", [True, False]),
        ('"string \\ ', [True, False]),
        ("'string ' ", [False, False]),
        ('"string " ', [False, False]),
        ("'string \"", [True, False]),
        ('"string \'', [True, False]),
        ("'string \" ", [True, False]),
        ('"string \' ', [True, False]),
        ("'''string ", [True, True]),
        ('"""string ', [True, True]),
        ("'''string \\", [True, True]),
        ('"""string \\', [True, True]),
        ("'''string \\ ", [True, True]),
        ('"""string \\ ', [True, True]),
        ("'''string ''' ", [False, False]),
        ('"""string """ ', [False, False]),
        ("'''string \"\"\"", [True, True]),
        ('"""string \'\'\'', [True, True]),
        ("'''string \"\"\" ", [True, True]),
        ('"""string \'\'\' ', [True, True]),
    ])
def test_in_string(editorbot, input_text, expected_state):
    """
    Test that in_string works correctly.
    """
    qtbot, widget = editorbot
    widget.set_text(input_text + '\n  ')
    cursor = widget.textCursor()

    for blanks_enabled in [True, False]:
        widget.set_blanks_enabled(blanks_enabled)

        cursor.setPosition(len(input_text))
        assert cursor.position() == len(input_text)
        assert widget.in_string(cursor) == expected_state[0]

        cursor.setPosition(len(input_text) + 3)
        assert widget.in_string(cursor) == expected_state[1]


if __name__ == '__main__':
    pytest.main(['test_codeeditor.py'])

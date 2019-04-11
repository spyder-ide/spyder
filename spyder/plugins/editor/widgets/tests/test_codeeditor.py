# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

# Third party imports
from qtpy.QtCore import Qt
from qtpy.QtGui import QFont, QTextCursor
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

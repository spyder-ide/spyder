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


def test_close_quotes(qtbot, editor_close_quotes):
    """"""
    editor = editor_close_quotes

    qtbot.keyClicks(editor, '"')
    assert editor.toPlainText() == '""'


if __name__ == '__main__':
    pytest.main()

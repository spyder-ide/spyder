# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for texteditor.py
"""

# Test library imports
import pytest

# Local imports
from spyder.py3compat import PY3
from spyder.plugins.variableexplorer.widgets.texteditor import TextEditor


TEXT = """01234567890123456789012345678901234567890123456789012345678901234567890123456789
dedekdh elkd ezd ekjd lekdj elkdfjelfjk e"""


@pytest.fixture
def texteditor(qtbot):
    """Set up TextEditor."""
    def create_texteditor(text, **kwargs):
        editor = TextEditor(text, **kwargs)
        qtbot.addWidget(editor)
        return editor
    return create_texteditor


def test_texteditor(texteditor):
    """Run TextEditor dialog."""
    editor = texteditor(TEXT)
    editor.show()
    assert editor
    dlg_text = editor.get_value()
    assert TEXT == dlg_text


@pytest.mark.skipif(PY3, reason="It makes no sense in Python 3")
def test_texteditor_setup_and_check(texteditor):
    import string
    dig_its = string.digits
    translate_digits = string.maketrans(dig_its,len(dig_its)*' ')

    editor = texteditor(None)
    assert not editor.setup_and_check(translate_digits)


@pytest.mark.parametrize("title", [u"ñ", u"r"])
def test_title(texteditor, title):
    editor = texteditor(TEXT, title=title)
    editor.show()
    dlg_title = editor.windowTitle()
    assert title in dlg_title


if __name__ == "__main__":
    pytest.main()

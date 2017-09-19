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
from spyder.py3compat import PY2
from spyder.plugins.variableexplorer.widgets.texteditor import TextEditor

@pytest.fixture
def setup_texteditor(qtbot, text):
    """Set up TextEditor."""
    texteditor = TextEditor(text)
    qtbot.addWidget(texteditor)
    return texteditor

def test_texteditor(qtbot):
    """Run TextEditor dialog."""
    text = """01234567890123456789012345678901234567890123456789012345678901234567890123456789
dedekdh elkd ezd ekjd lekdj elkdfjelfjk e"""
    texteditor = setup_texteditor(qtbot, text)
    texteditor.show()
    assert texteditor
    dlg_text = texteditor.get_value()
    assert text == dlg_text

def test_texteditor_setup_and_check():
    if PY2:
        import string
        dig_its = string.digits;
        translate_digits = string.maketrans(dig_its,len(dig_its)*' ')
        editor = TextEditor(None)
        assert not editor.setup_and_check(translate_digits)
    else:
        assert True


if __name__ == "__main__":
    pytest.main()

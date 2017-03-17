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
from spyder.widgets.variableexplorer.texteditor import TextEditor

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


if __name__ == "__main__":
    pytest.main()

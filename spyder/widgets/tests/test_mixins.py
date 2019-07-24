# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

# Third party imports
from qtpy.QtWidgets import QPlainTextEdit

import pytest

# Local imports
from spyder.widgets import mixins


class BaseWidget(QPlainTextEdit, mixins.BaseEditMixin):
    pass


# --- Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def mixinsbot(qtbot):
    widget = BaseWidget()
    qtbot.addWidget(widget)
    widget.show()
    return qtbot, widget

# --- Tests
# -----------------------------------------------------------------------------
def test_get_unicode_regexp(mixinsbot):
    """
    Test that we can search with regexp's containing unicode
    characters.

    For spyder-ide/spyder#6812.
    """
    qtbot, widget = mixinsbot
    get = widget.get_number_matches

    # CodeEditor and findreplace texts are handled in
    # unicode by PyQt5 in Python 2
    code = (u'print("И")\n'
            u'foo("И")')
    widget.setPlainText(code)
    cursor = widget.textCursor()
    cursor.setPosition(widget.get_position('sof'))
    assert widget.find_text(u't.*И', regexp=True)
    assert get(u't.*И', source_text=code, regexp=True) == 1


def test_get_number_matches(mixinsbot):
    # Test get_number_matches().
    qtbot, widget = mixinsbot
    get = widget.get_number_matches

    code = ('class C():\n'
            '    def __init__(self):\n'
            '        pass\n'
            '    def f(self, a, b):\n'
            '        pass\n')

    # Empty pattern.
    assert get('') == 0

    # No case, no regexp.
    assert get('self', source_text=code) == 2
    assert get('c', source_text=code) == 2

    # Case, no regexp.
    assert get('self', source_text=code, case=True) == 2
    assert get('c', source_text=code, case=True) == 1

    # No case, regexp.
    assert get('e[a-z]?f', source_text=code, regexp=True) == 4
    assert get('e[A-Z]?f', source_text=code, regexp=True) == 4

    # Case, regexp.
    assert get('e[a-z]?f', source_text=code, case=True, regexp=True) == 4
    assert get('e[A-Z]?f', source_text=code, case=True, regexp=True) == 2

    # No case, regexp, word
    assert get('e[a-z]?f', source_text=code, regexp=True, word=True) == 0
    assert get('e[A-Z]?f', source_text=code, regexp=True, word=True) == 0

    # Case, regexp, word
    assert get('e[a-z]?f', source_text=code, case=True, regexp=True,
               word=True) == 0
    assert get('e[A-Z]?f', source_text=code, case=True, regexp=True,
               word=True) == 0

    # spyder-ide/spyder#5680.
    assert get('(', source_text=code) == 3
    assert get('(', source_text=code, case=True) == 3
    assert get('(', source_text=code, regexp=True) is None
    assert get('(', source_text=code, case=True, regexp=True) is None

    # spyder-ide/spyder#7960.
    assert get('a', source_text=code) == 4
    assert get('a', source_text=code, case=True) == 4
    assert get('a', source_text=code, regexp=True) == 4
    assert get('a', source_text=code, case=True, regexp=True) == 4
    assert get('a', source_text=code, case=True, regexp=True, word=True) == 1
    assert get('a', source_text=code, regexp=True, word=True) == 1
    assert get('a', source_text=code, case=True, word=True) == 1


def test_get_match_number(mixinsbot):
    # Test get_match_number().
    qtbot, widget = mixinsbot
    get = widget.get_match_number

    code = ('class C():\n'
            '    def __init__(self):\n'
            '        pass\n'
            '    def f(self, a, b):\n'
            '        pass\n')
    widget.setPlainText(code)
    cursor = widget.textCursor()
    cursor.setPosition(widget.get_position('sof'))

    # Empty pattern.
    assert get('') == 0

    # spyder-ide/spyder#5680.
    widget.find_text('(')
    assert get('(') == 1

    # First occurrence.
    widget.find_text('self')
    assert get('self') == 1
    assert get('self', case=True) == 1

    # Second occurrence.
    widget.find_text('pass')
    widget.find_text('self')
    assert get('self') == 2
    assert get('self', case=True) == 2


def test_get_number_with_words(mixinsbot):
    """
    Test that find count honours the word setting.

    Dedicated test for spyder-ide/spyder#7960.
    """
    qtbot, widget = mixinsbot
    getn = widget.get_number_matches
    getm = widget.get_match_number

    code = ('word\n'
            'words\n'
            'Word\n'
            'Words\n'
            'sword\n'
            'word\n')

    widget.setPlainText(code)
    cursor = widget.textCursor()
    cursor.setPosition(widget.get_position('sof'))

    widget.find_text('Word')
    # Six instances of the string in total
    assert getn('Word', source_text=code) == 6
    # Found the first
    assert getm('Word') == 1
    # Two with same casing
    assert getn('Word', source_text=code, case=True) == 2
    # Three [Ww]ord in total
    assert getn('Word', source_text=code, word=True) == 3
    # But only one Word
    assert getn('Word', source_text=code, word=True, case=True) == 1
    # Find next Word case sensitive
    widget.find_text('Word', case=True)
    # This also moves to third row and first instance of Word (case sensitive)
    assert getm('Word', case=True) == 1
    # So this should be the third instance if case not considered
    assert getm('Word') == 3
    # But the second (out of the three) which is [Ww]ord
    assert getm('Word', word=True) == 2
    # Find something on next line just to progress
    widget.find_text('Words')
    # Find next [Ww]ord word-sensitive
    widget.find_text('Word', word=True)
    # This should be the sixth instance if case not considered
    assert getm('Word') == 6
    # But the third (out of the three) which is [Ww]ord
    assert getm('Word', word=True) == 3

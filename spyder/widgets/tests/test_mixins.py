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
    # For issue 6812
    qtbot, widget = mixinsbot
    get = widget.get_number_matches

    code = (u'print("И")\n'
             'foo("И")')
    widget.setPlainText(code)
    cursor = widget.textCursor()
    cursor.setPosition(widget.get_position('sof'))
    assert widget.find_text('t.*И', regexp=True)
    assert get('t.*И', source_text=code, regexp=True) == 1


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

    # Issue 5680.
    assert get('(', source_text=code) == 3
    assert get('(', source_text=code, case=True) == 3
    assert get('(', source_text=code, regexp=True) is None
    assert get('(', source_text=code, case=True, regexp=True) is None


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

    # Issue 5680.
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

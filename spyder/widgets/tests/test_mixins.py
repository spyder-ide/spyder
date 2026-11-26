# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

# Standard library imports
from unittest.mock import Mock

# Third party imports
from qtpy.QtCore import QEvent, QPoint, QPointF, Qt, QUrl
from qtpy.QtGui import QMouseEvent
from qtpy.QtWidgets import QApplication, QPlainTextEdit

import pytest

# Local imports
from spyder.widgets import mixins


class BaseWidget(mixins.BaseEditMixin, QPlainTextEdit):

    def __init__(self, parent=None):
        QPlainTextEdit.__init__(self, parent)
        mixins.BaseEditMixin.__init__(self)


class LinksWidget(mixins.TracebackLinksMixin, BaseWidget):
    QT_CLASS = QPlainTextEdit

    def __init__(self, parent=None):
        BaseWidget.__init__(self, parent)
        mixins.TracebackLinksMixin.__init__(self)


def send_mouse_event(widget, event_type, pos, button=Qt.LeftButton):
    """Send a mouse event to the viewport of widget at pos."""
    if event_type == QEvent.MouseMove:
        buttons = Qt.NoButton
        button = Qt.NoButton
    elif event_type == QEvent.MouseButtonPress:
        buttons = button
    else:
        buttons = Qt.NoButton

    event = QMouseEvent(
        event_type,
        QPointF(pos),
        QPointF(widget.viewport().mapToGlobal(pos)),
        button,
        buttons,
        Qt.NoModifier,
    )
    QApplication.sendEvent(widget.viewport(), event)


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
@pytest.mark.parametrize(
    "test_object", [(u"test.attr = np.linalg.norm()\n",
                     [(None, 'test'),
                      (4,    'test'),
                      (1,    'test.attr'),
                      (4,    'test.attr'),
                      (1,     None),
                      (1,     'np'),
                      (4,     'np.linalg'),
                      (6,     'np.linalg'),
                      (1,     'np.linalg.norm'),
                      (4,     'np.linalg.norm'),
                      (1,     None)
                      ]),
                    (u"test$attr = np$linalg$norm()\n",
                     [(None, 'test'),
                      (4,    'test'),
                      (1,    'test$attr'),
                      (4,    'test$attr'),
                      (1,     None),
                      (1,     'np'),
                      (4,     'np$linalg'),
                      (6,     'np$linalg'),
                      (1,     'np$linalg$norm'),
                      (4,     'np$linalg$norm'),
                      (1,     None)
                      ])])
def test_get_current_object(mixinsbot, test_object):
    """
    Test that we can get the current object to get help for the console.

    For spyder-ide/spyder#11821
    """
    qtbot, widget = mixinsbot
    get_current_object = widget.get_current_object

    code, matches = test_object
    widget.setPlainText(code)
    cursor = widget.textCursor()
    cursor.setPosition(widget.get_position('sof'))

    for move, match in matches:
        if move is not None:
            widget.move_cursor(move)
        current_word = get_current_object()
        assert current_word == match


def test_get_current_word(mixinsbot):
    """
    Test that we can get the current word to get help for the editor.

    For spyder-ide/spyder#11267
    """
    qtbot, widget = mixinsbot
    get_current_word = widget.get_current_word

    code = (u'def foo(a, b, c)\n')
    widget.setPlainText(code)
    cursor = widget.textCursor()
    cursor.setPosition(widget.get_position('sof'))
    widget.move_cursor(7)
    current_word = get_current_word()
    assert current_word is None
    current_word = get_current_word(help_req=True)
    assert current_word == 'foo'


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


def test_click_url(qtbot, monkeypatch):
    """Check that urls in plain text are underlined on hover and opened"""
    widget = LinksWidget()
    widget.setLineWrapMode(QPlainTextEdit.WidgetWidth)
    qtbot.addWidget(widget)
    widget.show()

    url = 'https://www.spyder-ide.org/blog'
    text = f'Plain text \nPlease visit {url} for more info'
    widget.setPlainText(text)

    open_url = Mock()
    monkeypatch.setattr(mixins.QDesktopServices, 'openUrl', open_url)

    def get_coordinates(position):
        """Get coordinates on top of the character at position"""
        cursor = widget.textCursor()
        cursor.setPosition(position)
        rect = widget.cursorRect(cursor)
        return QPoint(rect.left() + 2, rect.center().y())

    # Check url detection when it's wrapped in two lines
    width = widget.fontMetrics().horizontalAdvance('Please visit https://')
    widget.resize(width + 40, 200)
    qtbot.wait(100)

    first_line_pos = get_coordinates(text.index(url) + 2)
    second_line_pos = get_coordinates(text.index(url) + len(url) - 2)
    assert first_line_pos.y() < second_line_pos.y()
    assert widget.get_url_at(first_line_pos)[0] == url
    assert widget.get_url_at(second_line_pos)[0] == url

    # Check url detection in a single line
    widget.resize(1000, 200)
    qtbot.wait(100)

    url_pos = get_coordinates(text.index(url) + 5)
    text_pos = get_coordinates(text.index('info'))
    assert widget.get_url_at(url_pos)[0] == url
    assert widget.get_url_at(text_pos) == (None, None)

    # Check there's no url detected next to it
    assert widget.get_url_at(get_coordinates(text.index(url) - 2)) == (
        None, 
        None,
    )

    # Check url is underlined on hover
    send_mouse_event(widget, QEvent.MouseMove, url_pos)
    assert widget.anchor == url
    underlines = [
        s for s in widget.extraSelections()
        if s.format.boolProperty(mixins.URL_UNDERLINE_PROPERTY)
    ]
    assert len(underlines) == 1
    assert underlines[0].cursor.selectedText() == url

    # Check underline is removed when moving away from the url
    send_mouse_event(widget, QEvent.MouseMove, text_pos)
    assert widget.anchor is None
    assert widget.extraSelections() == []

    # Check right clicks don't open the url
    send_mouse_event(widget, QEvent.MouseMove, url_pos)
    send_mouse_event(
        widget, QEvent.MouseButtonRelease, url_pos, button=Qt.RightButton
    )
    open_url.assert_not_called()

    # Check left click opens it
    send_mouse_event(widget, QEvent.MouseButtonPress, url_pos)
    send_mouse_event(widget, QEvent.MouseButtonRelease,  url_pos)
    open_url.assert_called_once_with(QUrl(url))
    assert widget.extraSelections() == []
    
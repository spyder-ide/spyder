# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

# Standard library imports
import os
import tempfile

# Third party imports
import pytest
from qtpy.QtGui import QTextOption

# Local imports
from spyder.config.base import get_conf_path
from spyder.config.manager import CONF
from spyder.plugins.history import plugin as history


# =============================================================================
# Utillity Functions
# =============================================================================
def create_file(name, content):
    path = os.path.join(tempfile.gettempdir(), name)
    with open(path, 'w') as fh:
        fh.write(content)

    return path


# =============================================================================
# Qt Test Fixtures
# =============================================================================
@pytest.fixture
def historylog(qtbot):
    """
    Return a fixture for base history log, which is a plugin widget.
    """
    historylog = history.HistoryLog(None, configuration=CONF)
    historylog.close = lambda: True
    qtbot.addWidget(historylog.get_widget())
    historylog.get_widget().show()
    yield historylog
    historylog.on_close()
    historylog.close()


# =============================================================================
# Tests
# =============================================================================
def test_init(historylog):
    """
    Test HistoryLog

    Test that the initialization created the expected instance variables
    and widgets for a new HistoryLog instance.
    """
    hl = historylog
    assert len(hl.get_widget().editors) == 1
    assert len(hl.get_widget().filenames) == 1
    assert len(hl.get_actions()) == 7


def test_add_history(historylog):
    """
    Test the add_history method.

    Test adding a history file to the history log widget and the
    code editor properties that are enabled/disabled.
    """
    hl = historylog
    hw = historylog.get_widget()

    # No editors yet.
    assert len(hw.editors) == 1

    # Add one file.
    name1 = 'test_history.py'
    text1 = 'a = 5\nb= 10\na + b\n'
    path1 = create_file(name1, text1)
    tab1 = os.path.basename(path1)
    hw.set_conf('line_numbers', False)
    hw.set_conf('wrap', False)
    hl.add_history(path1)

    # Check tab and editor were created correctly.
    assert len(hw.editors) == 2
    assert hw.filenames == [get_conf_path('history.py'), path1]
    assert hw.tabwidget.currentIndex() == 1
    assert not hw.editors[0].linenumberarea.isVisible()
    assert hw.editors[0].wordWrapMode() == QTextOption.NoWrap
    assert hw.tabwidget.tabText(1) == tab1
    assert hw.tabwidget.tabToolTip(1) == path1

    # Try to add same file -- does not process filename again, so
    # linenumbers and wrap doesn't change.
    hw.add_history(path1)
    assert hw.tabwidget.currentIndex() == 1
    # assert not hw.editors[0].linenumberarea.isVisible()

    # Add another file.
    name2 = 'history2.js'
    text2 = 'random text\nspam line\n\n\n\n'
    path2 = create_file(name2, text2)
    tab2 = os.path.basename(path2)
    hw.set_conf('line_numbers', True)
    hw.set_conf('wrap', True)
    hw.add_history(path2)

    # Check second tab and editor were created correctly.
    assert len(hw.editors) == 3
    assert hw.filenames == [get_conf_path('history.py'), path1, path2]
    assert hw.tabwidget.currentIndex() == 2
    assert hw.editors[2].wordWrapMode() == (
        QTextOption.WrapAtWordBoundaryOrAnywhere)
    assert hw.editors[2].linenumberarea.isVisible()
    assert hw.tabwidget.tabText(2) == tab2
    assert hw.tabwidget.tabToolTip(2) == path2

    # Check differences between tabs based on setup.
    assert hw.editors[1].supported_language
    assert hw.editors[1].isReadOnly()
    assert not hw.editors[1].isVisible()
    assert hw.editors[1].toPlainText() == text1

    assert not hw.editors[2].supported_language
    assert hw.editors[2].isReadOnly()
    assert hw.editors[2].isVisible()
    assert hw.editors[2].toPlainText() == text2


def test_append_to_history(qtbot, historylog):
    """
    Test the append_to_history method.

    Test adding text to a history file.  Also test the go_to_eof config
    option for positioning the cursor.
    """
    hw = historylog.get_widget()

    # Toggle to move to the end of the file after appending.
    hw.set_conf('go_to_eof', True)

    # Force cursor to the beginning of the file.
    text1 = 'import re\n'
    path1 = create_file('test_history.py', text1)
    hw.add_history(path1)
    hw.editors[1].set_cursor_position('sof')
    hw.append_to_history(path1, 'foo = "bar"\n')
    assert hw.editors[1].toPlainText() == text1 + 'foo = "bar"\n'
    assert hw.tabwidget.currentIndex() == 1

    # Cursor moved to end.
    assert hw.editors[1].is_cursor_at_end()
    assert not hw.editors[1].linenumberarea.isVisible()

    # Toggle to not move cursor after appending.
    hw.set_conf('go_to_eof', False)

    # Force cursor to the beginning of the file.
    hw.editors[1].set_cursor_position('sof')
    hw.append_to_history(path1, 'a = r"[a-z]"\n')
    assert hw.editors[1].toPlainText() == ('import re\n'
                                           'foo = "bar"\n'
                                           'a = r"[a-z]"\n')

    # Cursor not at end.
    assert not hw.editors[1].is_cursor_at_end()


def test_toggle_wrap_mode(historylog):
    """
    Test the toggle_wrap_mode method.

    Toggle the 'Wrap lines' config action.
    """
    hw = historylog.get_widget()
    path = create_file('test.py', 'a = 1')
    hw.add_history(path)

    # Starts with wrap mode off.
    hw.set_conf('wrap', False)
    assert hw.editors[1].wordWrapMode() == QTextOption.NoWrap
    assert not hw.get_conf('wrap')

    # Toggles wrap mode on.
    hw.set_conf('wrap', True)
    assert hw.editors[1].wordWrapMode() == (
        QTextOption.WrapAtWordBoundaryOrAnywhere)
    assert hw.get_conf('wrap')

    # Toggles wrap mode off.
    hw.set_conf('wrap', False)
    assert hw.editors[1].wordWrapMode() == QTextOption.NoWrap
    assert not hw.get_conf('wrap')


def test_toggle_line_numbers(historylog):
    """
    Test toggle_line_numbers method.

    Toggle the 'Show line numbers' config action.
    """
    hw = historylog.get_widget()
    path = create_file('test.py', 'a = 1')
    hw.add_history(path)

    # Starts without line numbers.
    hw.set_conf('line_numbers', False)
    assert not hw.editors[1].linenumberarea.isVisible()
    assert not hw.get_conf('line_numbers')

    # Toggles line numbers on.
    hw.set_conf('line_numbers', True)
    assert hw.editors[1].linenumberarea.isVisible()
    assert hw.get_conf('line_numbers')

    # Toggles line numbers off.
    hw.set_conf('line_numbers', False)
    assert not hw.editors[1].linenumberarea.isVisible()
    assert not hw.get_conf('line_numbers')


if __name__ == "__main__":
    pytest.main()

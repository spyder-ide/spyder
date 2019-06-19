# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

import pytest

from qtpy.QtGui import QTextOption

from spyder.plugins.history import plugin as history
from spyder.py3compat import to_text_string

#==============================================================================
# Utillity Functions
#==============================================================================
options = {'wrap': False,
           'line_numbers': False,
           'go_to_eof': True,
           'max_entries': 100}


def get_option(self, option):
    global options
    return options[option]


def set_option(self, option, value):
    global options
    options[option] = value

#==============================================================================
# Qt Test Fixtures
#==============================================================================
@pytest.fixture
def historylog(qtbot, monkeypatch):
    """Return a fixture for base history log, which is a plugin widget."""
    monkeypatch.setattr(history.HistoryLog,
                        'register_widget_shortcuts',
                        lambda *args: None)
    historylog = history.HistoryLog(None)
    historylog._setup()
    qtbot.addWidget(historylog)
    historylog.show()
    yield historylog
    historylog.closing_plugin()
    historylog.close()


@pytest.fixture
def historylog_with_tab(historylog, mocker, monkeypatch):
    """Return a fixture for a history log with one tab.

    The base history log is a plugin widget.  Within the plugin widget,
    the method add_history creates a tab containing a code editor
    for each history file.  This fixture creates a history log with
    one tab containing no text.
    """
    hl = historylog
    # Mock read so file doesn't have to exist.
    mocker.patch.object(history.encoding, 'read')
    history.encoding.read.return_value = ('', '')

    # Monkeypatch current options.
    monkeypatch.setattr(history.HistoryLog, 'get_option', get_option)
    monkeypatch.setattr(history.HistoryLog, 'set_option', set_option)

    # Create tab for page.
    hl.set_option('wrap', False)
    hl.set_option('line_numbers', False)
    hl.set_option('max_entries', 100)
    hl.set_option('go_to_eof', True)
    hl.add_history('test_history.py')
    return hl

#==============================================================================
# Tests
#==============================================================================
def test_max_entries(historylog, tmpdir):
    """Test that history is truncated at max_entries."""
    max_entries = historylog.get_option('max_entries')

    # Write more than max entries in a test file
    history = ''
    for i in range(max_entries + 1):
        history = history + '{}\n'.format(i)

    history_file = tmpdir.join('history.py')
    history_file.write(history)

    # Load test file in plugin
    historylog.add_history(to_text_string(history_file))

    # Assert that we have max_entries after loading history and
    # that there's no 0 in the first line
    assert len(history_file.readlines()) == max_entries
    assert '0' not in history_file.readlines()[0]


def test_init(historylog):
    """Test HistoryLog.__init__.

    Test that the initialization created the expected instance variables
    and widgets for a new HistoryLog instance.
    """
    hl = historylog
    assert hl.editors == []
    assert hl.filenames == []
    assert len(hl._plugin_actions) == 5
    assert len(hl.tabwidget.cornerWidget().menu().actions()) == 5


def test_add_history(historylog, mocker, monkeypatch):
    """Test the add_history method.

    Test adding a history file to the history log widget and the
    code editor properties that are enabled/disabled.
    """
    hl = historylog
    hle = hl.editors

    # Mock read so file doesn't have to exist.
    mocker.patch.object(history.encoding, 'read')

    # Monkeypatch current options.
    monkeypatch.setattr(history.HistoryLog, 'get_option', get_option)
    monkeypatch.setattr(history.HistoryLog, 'set_option', set_option)
    # No editors yet.
    assert len(hl.editors) == 0

    # Add one file.
    tab1 = 'test_history.py'
    text1 = 'a = 5\nb= 10\na + b\n'
    hl.set_option('line_numbers', False)
    hl.set_option('wrap', False)
    history.encoding.read.return_value = (text1, '')
    hl.add_history(tab1)
    # Check tab and editor were created correctly.
    assert len(hle) == 1
    assert hl.filenames == [tab1]
    assert hl.tabwidget.currentIndex() == 0
    assert not hle[0].linenumberarea.isVisible()
    assert hle[0].wordWrapMode() == QTextOption.NoWrap
    assert hl.tabwidget.tabText(0) == tab1
    assert hl.tabwidget.tabToolTip(0) == tab1

    hl.set_option('line_numbers', True)
    hl.set_option('wrap', True)
    # Try to add same file -- does not process filename again, so
    # linenumbers and wrap doesn't change.
    hl.add_history(tab1)
    assert hl.tabwidget.currentIndex() == 0
    assert not hl.editors[0].linenumberarea.isVisible()

    # Add another file.
    tab2 = 'history2.js'
    text2 = 'random text\nspam line\n\n\n\n'
    history.encoding.read.return_value = (text2, '')
    hl.add_history(tab2)
    # Check second tab and editor were created correctly.
    assert len(hle) == 2
    assert hl.filenames == [tab1, tab2]
    assert hl.tabwidget.currentIndex() == 1
    assert hle[1].linenumberarea.isVisible()
    assert hle[1].wordWrapMode() == QTextOption.WrapAtWordBoundaryOrAnywhere
    assert hl.tabwidget.tabText(1) == tab2
    assert hl.tabwidget.tabToolTip(1) == tab2

    assert hl.filenames == [tab1, tab2]

    # Check differences between tabs based on setup.
    assert hle[0].supported_language
    assert hle[0].is_python()
    assert hle[0].isReadOnly()
    assert not hle[0].isVisible()
    assert hle[0].toPlainText() == text1

    assert not hle[1].supported_language
    assert not hle[1].is_python()
    assert hle[1].isReadOnly()
    assert hle[1].isVisible()
    assert hle[1].toPlainText() == text2


def test_append_to_history(historylog_with_tab, mocker):
    """Test the append_to_history method.

    Test adding text to a history file.  Also test the go_to_eof config
    option for positioning the cursor.
    """
    hl = historylog_with_tab

    # Toggle to move to the end of the file after appending.
    hl.set_option('go_to_eof', True)
    # Force cursor to the beginning of the file.
    hl.editors[0].set_cursor_position('sof')
    hl.append_to_history('test_history.py', 'import re\n')
    assert hl.editors[0].toPlainText() == 'import re\n'
    assert hl.tabwidget.currentIndex() == 0
    # Cursor moved to end.
    assert hl.editors[0].is_cursor_at_end()
    assert not hl.editors[0].linenumberarea.isVisible()

    # Toggle to not move cursor after appending.
    hl.set_option('go_to_eof', False)
    # Force cursor to the beginning of the file.
    hl.editors[0].set_cursor_position('sof')
    hl.append_to_history('test_history.py', 'a = r"[a-z]"\n')
    assert hl.editors[0].toPlainText() == 'import re\na = r"[a-z]"\n'
    # Cursor not at end.
    assert not hl.editors[0].is_cursor_at_end()


def test_change_history_depth(historylog_with_tab, mocker):
    """Test the change_history_depth method.

    Modify the 'Maximum history entries' values to test the config action.
    """
    hl = historylog_with_tab
    action = hl.history_action
    # Mock dialog.
    mocker.patch.object(history.QInputDialog, 'getInt')

    # Starts with default.
    assert hl.get_option('max_entries') == 100

    # Invalid data.
    history.QInputDialog.getInt.return_value = (10, False)
    action.trigger()
    assert hl.get_option('max_entries') == 100  # No change.

    # Valid data.
    history.QInputDialog.getInt.return_value = (475, True)
    action.trigger()
    assert hl.get_option('max_entries') == 475


def test_toggle_wrap_mode(historylog_with_tab):
    """Test the toggle_wrap_mode method.

    Toggle the 'Wrap lines' config action.
    """
    hl = historylog_with_tab
    action = hl.wrap_action
    action.setChecked(False)

    # Starts with wrap mode off.
    assert hl.editors[0].wordWrapMode() == QTextOption.NoWrap
    assert not hl.get_option('wrap')

    # Toggles wrap mode on.
    action.setChecked(True)
    assert hl.editors[0].wordWrapMode() == QTextOption.WrapAtWordBoundaryOrAnywhere
    assert hl.get_option('wrap')

    # Toggles wrap mode off.
    action.setChecked(False)
    assert hl.editors[0].wordWrapMode() == QTextOption.NoWrap
    assert not hl.get_option('wrap')


def test_toggle_line_numbers(historylog_with_tab):
    """Test toggle_line_numbers method.

    Toggle the 'Show line numbers' config action.
    """
    hl = historylog_with_tab
    action = hl.linenumbers_action
    action.setChecked(False)

    # Starts without line numbers.
    assert not hl.editors[0].linenumberarea.isVisible()
    assert not hl.get_option('line_numbers')

    # Toggles line numbers on.
    action.setChecked(True)
    assert hl.editors[0].linenumberarea.isVisible()
    assert hl.get_option('line_numbers')

    # Toggles line numbers off.
    action.setChecked(False)
    assert not hl.editors[0].linenumberarea.isVisible()
    assert not hl.get_option('line_numbers')


if __name__ == "__main__":
    pytest.main()

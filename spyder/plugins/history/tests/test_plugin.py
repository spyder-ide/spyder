# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

# Standard library imports
from unittest.mock import MagicMock

# Third party imports
import pytest
from qtpy.QtGui import QTextOption

# Local imports
from spyder.config.manager import CONF
from spyder.plugins.history import plugin as history
from spyder.plugins.history import widgets as history_widgets


# =============================================================================
# Qt Test Fixtures
# =============================================================================
@pytest.fixture
def ipython_history(monkeypatch):
    """Fake the commands loaded from IPython's history database.

    This avoids reading the real history of whoever runs the tests.
    """
    commands = ['import numpy as np', 'a = 1\nb = 2', 'a + b']
    monkeypatch.setattr(
        history_widgets, 'load_ipython_history', lambda: list(commands)
    )
    return commands


@pytest.fixture
def historylog(qtbot, ipython_history):
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


@pytest.fixture
def shellwidgets():
    """Return two fake shell widgets.

    ShellConnectMainWidget only needs them to be distinct objects.
    """
    return MagicMock(), MagicMock()


# =============================================================================
# Tests
# =============================================================================
def test_init(historylog):
    """
    Test that a new HistoryLog starts without editors (one is created for each
    console) and has the expected actions.
    """
    hl = historylog
    assert hl.get_widget().count() == 0
    assert len(hl.get_actions()) == 8


def test_add_and_remove_shellwidget(historylog, shellwidgets):
    """Test that each console gets its own read-only editor."""
    hl = historylog
    hw = hl.get_widget()
    shell1, shell2 = shellwidgets

    hl.add_shellwidget(shell1)
    hl.add_shellwidget(shell2)
    assert hw.count() == 2

    editor1 = hl.get_widget_for_shellwidget(shell1)
    editor2 = hl.get_widget_for_shellwidget(shell2)
    assert editor1 is not editor2
    assert editor1.isReadOnly()
    assert editor1.supported_language

    # The last console added is the current one.
    assert hl.current_widget() is editor2

    # Switching consoles shows the corresponding editor.
    hl.set_shellwidget(shell1)
    assert hl.current_widget() is editor1
    assert hw.find_widget.editor is editor1

    # Adding the same console again doesn't create another editor.
    hl.add_shellwidget(shell1)
    assert hw.count() == 2

    # Removing a console removes its editor.
    hl.remove_shellwidget(shell1)
    assert hw.count() == 1
    assert hl.get_widget_for_shellwidget(shell1) is None


def test_new_editors_start_with_ipython_history(
    historylog, shellwidgets, ipython_history
):
    """Test that each new editor is filled with the IPython history."""
    hl = historylog
    for shell in shellwidgets:
        hl.add_shellwidget(shell)
        editor = hl.get_widget_for_shellwidget(shell)
        assert editor.toPlainText() == "\n".join(ipython_history)
        assert editor.is_cursor_at_end()


def test_append_to_history(historylog, shellwidgets):
    """Test that commands go only to the editor of their console."""
    hl = historylog
    hw = hl.get_widget()
    shell1, shell2 = shellwidgets
    hl.add_shellwidget(shell1)
    hl.add_shellwidget(shell2)
    editor1 = hl.get_widget_for_shellwidget(shell1)
    editor2 = hl.get_widget_for_shellwidget(shell2)
    initial_text = editor1.toPlainText()

    # Command only added to the first console
    hw.set_conf('go_to_eof', True)
    editor1.set_cursor_position('sof')
    hl.append_to_history(shell1, 'foo = "bar"')
    assert editor1.toPlainText() == initial_text + '\nfoo = "bar"'
    assert editor2.toPlainText() == initial_text
    assert editor1.is_cursor_at_end()

    # Cursor shouldn't move when go_to_eof is disabled
    hw.set_conf('go_to_eof', False)
    editor1.set_cursor_position('sof')
    hl.append_to_history(shell1, 'a = r"[a-z]"')
    assert editor1.toPlainText().endswith('foo = "bar"\na = r"[a-z]"')
    assert not editor1.is_cursor_at_end()

    # Commands for unknown consoles are ignored
    hl.append_to_history(MagicMock(), 'ignored = True')
    assert 'ignored' not in editor1.toPlainText()
    assert 'ignored' not in editor2.toPlainText()


def test_append_to_empty_history(historylog, shellwidgets, monkeypatch):
    """Test that the first command doesn't start with a blank line."""
    monkeypatch.setattr(
        historylog.get_widget(), '_ipython_history', []
    )
    historylog.add_shellwidget(shellwidgets[0])
    historylog.append_to_history(shellwidgets[0], 'a = 1')
    editor = historylog.get_widget_for_shellwidget(shellwidgets[0])
    assert editor.toPlainText() == 'a = 1'


def test_load_ipython_history(tmp_path, monkeypatch):
    """Test loading commands from a real IPython history database."""
    import datetime

    from IPython.core.history import HistoryAccessor

    # Create a history database (HistoryAccessor creates the tables) and fill
    # it as IPython kernels do.
    hist_file = str(tmp_path / 'history.sqlite')
    accessor = HistoryAccessor(hist_file=hist_file)
    with accessor.db:
        accessor.db.execute(
            "INSERT INTO sessions VALUES (NULL, ?, NULL, NULL, '')",
            (datetime.datetime.now(),),
        )
        for i, cmd in enumerate(['x = 1', 'y = 2', 'x + y'], start=1):
            accessor.db.execute(
                "INSERT INTO history VALUES (?, ?, ?, ?)", (1, i, cmd, cmd)
            )
    accessor.db.close()

    monkeypatch.setattr(
        history_widgets,
        'HistoryAccessor',
        lambda: HistoryAccessor(hist_file=hist_file),
    )
    assert history_widgets.load_ipython_history() == [
        'x = 1', 'y = 2', 'x + y'
    ]
    assert history_widgets.load_ipython_history(max_entries=2) == [
        'y = 2', 'x + y'
    ]


def test_load_ipython_history_failure(monkeypatch):
    """Test that errors reading the history database are not propagated."""
    def raise_error():
        raise OSError("can't open history")

    monkeypatch.setattr(history_widgets, 'HistoryAccessor', raise_error)
    assert history_widgets.load_ipython_history() == []


def test_toggle_wrap_mode(historylog, shellwidgets):
    """
    Test the toggle_wrap_mode method.

    Toggle the 'Wrap lines' config action.
    """
    hl = historylog
    hw = hl.get_widget()
    for shell in shellwidgets:
        hl.add_shellwidget(shell)
    editors = [hl.get_widget_for_shellwidget(s) for s in shellwidgets]

    # Starts with wrap mode off.
    hw.set_conf('wrap', False)
    assert not hw.get_conf('wrap')
    assert all(e.wordWrapMode() == QTextOption.NoWrap for e in editors)

    # Toggles wrap mode on.
    hw.set_conf('wrap', True)
    assert hw.get_conf('wrap')
    assert all(
        e.wordWrapMode() == QTextOption.WrapAtWordBoundaryOrAnywhere
        for e in editors
    )

    # Toggles wrap mode off.
    hw.set_conf('wrap', False)
    assert not hw.get_conf('wrap')
    assert all(e.wordWrapMode() == QTextOption.NoWrap for e in editors)


def test_toggle_line_numbers(historylog, shellwidgets):
    """
    Test toggle_line_numbers method.

    Toggle the 'Show line numbers' config action.
    """
    hl = historylog
    hw = hl.get_widget()
    hl.add_shellwidget(shellwidgets[0])
    editor = hl.get_widget_for_shellwidget(shellwidgets[0])

    # Starts without line numbers.
    hw.set_conf('line_numbers', False)
    assert not editor.linenumberarea.isVisible()
    assert not hw.get_conf('line_numbers')

    # Toggles line numbers on.
    hw.set_conf('line_numbers', True)
    assert editor.linenumberarea.isVisible()
    assert hw.get_conf('line_numbers')

    # Toggles line numbers off.
    hw.set_conf('line_numbers', False)
    assert not editor.linenumberarea.isVisible()
    assert not hw.get_conf('line_numbers')


def test_options_with_errored_console(historylog, shellwidgets):
    """
    Test that changing options works when the kernel of a console failed to
    start, in which case an error message is shown instead of an editor.
    """
    hl = historylog
    hw = hl.get_widget()
    shell1, shell2 = shellwidgets
    hl.add_shellwidget(shell1)
    hl.add_shellwidget(shell2)
    hl.add_errored_shellwidget(shell2)

    # Show the working console, so that its line numbers can be visible.
    hl.set_shellwidget(shell1)
    editor = hl.get_widget_for_shellwidget(shell1)

    # Only the editor of the working console is changed.
    hw.set_conf('wrap', True)
    assert editor.wordWrapMode() == QTextOption.WrapAtWordBoundaryOrAnywhere
    hw.set_conf('wrap', False)
    assert editor.wordWrapMode() == QTextOption.NoWrap

    hw.set_conf('line_numbers', True)
    assert editor.linenumberarea.isVisible()
    hw.set_conf('line_numbers', False)
    assert not editor.linenumberarea.isVisible()

    hl.update_font()

    # Commands for the errored console are ignored.
    hl.append_to_history(shell2, 'ignored = True')
    assert 'ignored' not in editor.toPlainText()


if __name__ == "__main__":
    pytest.main()

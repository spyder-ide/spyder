# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# ----------------------------------------------------------------------------

"""Tests for status bar widgets."""

# Standard library imports
import os
import sys

# Thrid party imports
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QMainWindow
import pytest

# Local imports
from spyder.config import base
from spyder.utils import conda
from spyder.widgets.status import (BaseTimerStatus, CPUStatus,
                                   InterpreterStatus, MemoryStatus,
                                   StatusBarWidget)
import spyder.widgets.status


@pytest.fixture
def status_bar(qtbot):
    """Set up StatusBarWidget."""
    win = QMainWindow()
    win.setWindowTitle("Status widgets test")
    win.resize(900, 300)
    statusbar = win.statusBar()
    qtbot.addWidget(win)
    return (win, statusbar)


def test_status_bar_time_based_widgets(status_bar, qtbot):
    """Run StatusBarWidget."""
    win, statusbar = status_bar
    swidgets = []
    for klass in (MemoryStatus, CPUStatus):
        swidget = klass(win, statusbar)
        swidgets.append(swidget)
    assert win
    assert len(swidgets) == 2


class StatusBarWidgetTest(StatusBarWidget):
    def get_tooltip(self):
        return 'tooltip'

    def get_icon(self):
        return 'icon'


def test_status_bar_widget_signal(status_bar, qtbot):
    win, statusbar = status_bar
    w = StatusBarWidgetTest(win, statusbar)

    with qtbot.waitSignal(w.sig_clicked, timeout=1000):
        qtbot.mouseRelease(w, Qt.LeftButton)

    assert w.get_tooltip() == 'tooltip'
    assert w.get_icon() == 'icon'


def test_status_bar_conda_interpreter_status(status_bar, qtbot, mocker):
    # We patch where the method is used not where it is imported from
    mocker.patch.object(spyder.widgets.status, 'is_conda_env',
                        return_value=True)
    mock_py_ver = 'Python 6.6.6'

    win, statusbar = status_bar
    w = InterpreterStatus(win, statusbar)

    # Check that we process stdout and stderr correctly
    out_or_err = mock_py_ver + ' (hello!)'
    for (out, err) in [(out_or_err, ''), ('', out_or_err)]:
        # We patch the method that calls for info to return values to test
        mocker.patch.object(w, '_get_interpreter_env_info',
                            return_value=(out, err))

        if os.name == 'nt':
            interpreter = os.sep.join(['miniconda', 'python'])
        else:
            interpreter = os.sep.join(['miniconda', 'bin', 'python'])
        w.update_interpreter(interpreter)
        expected = 'conda: base (Python 6.6.6)'
        assert w.get_tooltip() == interpreter
        assert expected == w._process_interpreter_env_info()

        # We patch the method that calls for info to return values to test
        if os.name == 'nt':
            interpreter = os.sep.join(['miniconda', 'envs', 'foo', 'python'])
        else:
            interpreter = os.sep.join(['miniconda', 'envs', 'foo', 'bin',
                                       'python'])

        w.update_interpreter(interpreter)
        expected = 'conda: foo (Python 6.6.6)'
        assert w.get_tooltip() == interpreter
        assert expected == w._process_interpreter_env_info()


def test_status_bar_other_interpreter_status(status_bar, qtbot, mocker):
    mocker.patch.object(spyder.widgets.status, 'is_conda_env',
                        return_value=False)

    win, statusbar = status_bar
    w = InterpreterStatus(win, statusbar)
    mocker.patch.object(w, '_get_interpreter_env_info',
                        return_value=('Python 3.6.6', ''))

    interpreter = os.sep.join(['some-other', 'bin', 'python'])
    w.update_interpreter(interpreter)
    assert w.get_tooltip() == interpreter
    assert 'venv (Python 3.6.6)' == w._process_interpreter_env_info()


@pytest.mark.skipif(sys.platform != 'darwin', reason="Only valid on Mac")
def test_status_bar_internal_interpreter_status(status_bar, qtbot, mocker):
    mocker.patch.object(spyder.widgets.status, 'is_conda_env',
                        return_value=False)
    mocker.patch.object(spyder.widgets.status, 'running_in_mac_app',
                        return_value=True)

    win, statusbar = status_bar
    w = InterpreterStatus(win, statusbar)
    mocker.patch.object(w, '_get_interpreter_env_info',
                        return_value=('Python 3.6.6', ''))

    interpreter = os.sep.join(['Spyder.app', 'Contents', 'MacOS', 'Python'])
    w.update_interpreter(interpreter)
    assert w.get_tooltip() == interpreter
    assert 'internal (Python 3.6.6)' == w._process_interpreter_env_info()


if __name__ == "__main__":
    pytest.main()

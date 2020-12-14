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
from spyder.widgets.status import (BaseTimerStatus, CPUStatus,
                                   InterpreterStatus, MemoryStatus,
                                   StatusBarWidget)


@pytest.fixture
def status_bar(qtbot):
    """Set up StatusBarWidget."""
    win = QMainWindow()
    win.setWindowTitle("Status widgets test")
    win.resize(900, 300)
    statusbar = win.statusBar()
    win.show()
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


@pytest.mark.skipif(not bool(os.environ.get('CI')),
                    reason="Only meant for CIs")
def test_status_bar_conda_interpreter_status(status_bar, qtbot, mocker):
    """Test status bar message with conda interpreter."""
    # We patch where the method is used not where it is imported from
    win, statusbar = status_bar
    w = InterpreterStatus(win, statusbar)
    w._interpreter = ''

    name_base = 'conda: base'
    name_test = 'conda: test'

    # Wait until envs are computed
    qtbot.wait(4000)

    # Update to the base conda environment
    path_base, version = w.envs[name_base]
    w.update_interpreter(path_base)
    expected = 'conda: base ({})'.format(version)
    assert w.get_tooltip() == path_base
    assert expected == w._get_env_info(path_base)

    # Update to the foo conda environment
    path_foo, version = w.envs[name_test]
    w.update_interpreter(path_foo)
    expected = 'conda: test ({})'.format(version)
    assert w.get_tooltip() == path_foo
    assert expected == w._get_env_info(path_foo)


def test_status_bar_pyenv_interpreter_status(status_bar, qtbot, mocker):
    """Test status var message with pyenv interpreter."""
    win, statusbar = status_bar
    w = InterpreterStatus(win, statusbar)
    version = 'Python 3.6.6'
    name = 'pyenv: test'
    interpreter = os.sep.join(['some-other', 'bin', 'python'])
    w.envs = {name: (interpreter, version)}
    w.path_to_env = {interpreter: name}
    w.update_interpreter(interpreter)
    assert w.get_tooltip() == interpreter
    assert 'pyenv: test (Python 3.6.6)' == w._get_env_info(interpreter)


@pytest.mark.skipif(sys.platform != 'darwin', reason="Only valid on Mac")
def test_status_bar_internal_interpreter_status(status_bar, qtbot, mocker):
    """Test status bar message with internal interpreter."""
    # mocker.patch.object(spyder.widgets.status, 'running_in_mac_app',
    #                     return_value=True)

    win, statusbar = status_bar
    w = InterpreterStatus(win, statusbar)
    interpreter = os.sep.join(['Spyder.app', 'Contents', 'MacOS', 'Python'])
    name = 'system:'
    version = 'Python 3.6.6'
    w.envs = {name: (interpreter, version)}
    w.path_to_env = {interpreter: name}
    w.update_interpreter(interpreter)
    assert w.get_tooltip() == interpreter
    assert 'system: (Python 3.6.6)' == w._get_env_info(interpreter)


if __name__ == "__main__":
    pytest.main()

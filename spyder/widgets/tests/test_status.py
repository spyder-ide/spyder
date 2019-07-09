# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# ----------------------------------------------------------------------------

"""Tests for status bar widgets."""

# Test library imports
import pytest

# Thrid party imports
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QMainWindow

# Local imports
from spyder.config import utils
from spyder.widgets.status import (BaseTimerStatus, CondaStatus, CPUStatus,
                                   MemoryStatus, StatusBarWidget)


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


def test_status_bar_conda_status(status_bar, qtbot, mocker):
    mocker.patch.object(utils, 'is_anaconda', return_value=True)

    win, statusbar = status_bar
    w = CondaStatus(win, statusbar)

    interpreter = '/miniconda/bin/python'
    w.update_interpreter(interpreter)
    assert w.get_tooltip() == interpreter
    assert 'base' in w._process_conda_env_info()

    interpreter = '/miniconda/envs/foo/bin/python'
    w.update_interpreter(interpreter)
    assert w.get_tooltip() == interpreter
    assert 'foo' in w._process_conda_env_info()


def test_status_bar_no_conda_status(status_bar, qtbot, mocker):
    mocker.patch.object(utils, 'is_anaconda', return_value=False)
    win, statusbar = status_bar
    w = CondaStatus(win, statusbar)
    interpreter = '/some-other/bin/python'
    w.update_interpreter(interpreter)
    assert w.get_tooltip() == interpreter
    assert '' == w._process_conda_env_info()


if __name__ == "__main__":
    pytest.main()

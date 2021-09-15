# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tests for status bar widgets."""

# Thrid party imports
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QComboBox, QMainWindow
import pytest

# Local imports
from spyder.api.widgets.status import StatusBarWidget
from spyder.config.manager import CONF
from spyder.plugins.statusbar.plugin import StatusBar


class MainWindowMock(QMainWindow):
    pass


@pytest.fixture
def status_bar(qtbot):
    """Set up StatusBarWidget."""
    window = MainWindowMock()
    plugin = StatusBar(parent=window, configuration=CONF)
    plugin.remove_status_widgets()
    plugin.initialize()

    qtbot.addWidget(window)
    window.resize(640, 480)
    window.show()
    return (plugin, window)


def test_status_bar_default_widgets(status_bar, qtbot):
    """Run StatusBarWidget."""
    plugin, __ = status_bar

    # We create three widgets by default
    assert len(plugin.STATUS_WIDGETS) == 3


class StatusBarWidgetTest(StatusBarWidget):
    ID = 'test_status'

    def get_tooltip(self):
        return 'tooltip'

    def get_icon(self):
        return 'icon'


class MyComboBox(QComboBox):
    def __init__(self, parent):
        super().__init__(parent)
        self.addItems(['foo', 'bar'])


class CustomStatusBarWidget(StatusBarWidget):
    ID = 'custom_status'
    CUSTOM_WIDGET_CLASS = MyComboBox

    def get_icon(self):
        return self.create_icon('environment')


def test_status_bar_widget_signal(status_bar, qtbot):
    plugin, window = status_bar

    # Add widget to status bar
    w = StatusBarWidgetTest(window)
    plugin.add_status_widget(w)

    # We create three widgets by default
    assert len(plugin.STATUS_WIDGETS) == 4

    with qtbot.waitSignal(w.sig_clicked, timeout=1000):
        qtbot.mouseRelease(w, Qt.LeftButton)

    assert w.get_tooltip() == 'tooltip'
    assert w.get_icon() == 'icon'


def test_custom_widget(status_bar, qtbot):
    plugin, window = status_bar

    # Add widget to status bar
    w = CustomStatusBarWidget(window)
    w.set_value('Options: ')
    plugin.add_status_widget(w)
    # qtbot.stop()

    # We create three widgets by default
    assert len(plugin.STATUS_WIDGETS) == 4


if __name__ == "__main__":
    pytest.main()

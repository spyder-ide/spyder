# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License

"""Native dock tab styling when initially hidden panes are shown."""

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QMainWindow, QTabBar, QWidget

from spyder.widgets.dock import SpyderDockWidget


def test_hidden_dock_tabbar_is_centered_when_shown(qtbot):
    window = QMainWindow()
    qtbot.addWidget(window)
    window.resize(800, 500)
    docks = [SpyderDockWidget(title, window) for title in ('Editor', 'Secondary outline')]
    for dock in docks:
        dock.setWidget(QWidget())
        window.addDockWidget(Qt.LeftDockWidgetArea, dock)
        dock.hide()
    window.tabifyDockWidget(*docks)
    for dock in docks:
        dock.is_shown = True
        dock.install_tab_event_filter()
    window.show()
    docks[0].show()
    for _ in range(2):
        docks[1].show()
        docks[1].raise_()
        qtbot.wait(50)
        tabbar = next(bar for bar in window.findChildren(QTabBar) if bar.isVisible())
        bounds = tabbar.tabRect(0).united(tabbar.tabRect(1))
        assert abs(bounds.center().x() - tabbar.rect().center().x()) <= 2
        docks[1].hide()

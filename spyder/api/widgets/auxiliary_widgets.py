# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder API auxiliary widgets.
"""

# Third party imports
from qtpy.QtCore import QEvent, QSize, Signal
from qtpy.QtWidgets import QMainWindow, QSizePolicy, QToolBar, QWidget

# Local imports
from spyder.api.exceptions import SpyderAPIError
from spyder.api.widgets.mixins import SpyderMainWindowMixin
from spyder.utils.stylesheet import APP_STYLESHEET


class SpyderWindowWidget(QMainWindow, SpyderMainWindowMixin):
    """MainWindow subclass that contains a SpyderDockablePlugin."""

    # ---- Signals
    # ------------------------------------------------------------------------
    sig_closed = Signal()
    """This signal is emitted when the close event is fired."""

    sig_window_state_changed = Signal(object)
    """
    This signal is emitted when the window state has changed (for instance,
    between maximized and minimized states).

    Parameters
    ----------
    window_state: Qt.WindowStates
        The window state.
    """

    def __init__(self, widget):
        super().__init__()
        self.widget = widget

        # To distinguish these windows from the main Spyder one
        self.is_window_widget = True

        # Setting interface theme
        self.setStyleSheet(str(APP_STYLESHEET))

    def closeEvent(self, event):
        """Override Qt method to emit a custom `sig_close` signal."""
        super().closeEvent(event)
        self.sig_closed.emit()

    def changeEvent(self, event):
        """
        Override Qt method to emit a custom `sig_windowstate_changed` signal
        when there's a change in the window state.
        """
        if event.type() == QEvent.WindowStateChange:
            self.sig_window_state_changed.emit(self.windowState())
        super().changeEvent(event)


class MainCornerWidget(QToolBar):
    """
    Corner widget to hold options menu, spinner and additional options.
    """

    def __init__(self, parent, name):
        super().__init__(parent)
        self._icon_size = QSize(16, 16)
        self.setIconSize(self._icon_size)

        self._widgets = {}
        self._actions = []
        self.setObjectName(name)

        # We add an strut widget here so that there is a spacing
        # between the first item of the corner widget and the last
        # item of the MainWidgetToolbar.
        self._strut = QWidget()
        self._strut.setFixedWidth(0)
        self._strut.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.addWidget(self._strut)

    def add_widget(self, widget_id, widget):
        """
        Add a widget to the left of the last widget added to the corner.
        """
        if widget_id in self._widgets:
            raise SpyderAPIError(
                'Wigdet with name "{}" already added. Current names are: {}'
                ''.format(widget_id, list(self._widgets.keys()))
            )

        widget.ID = widget_id
        self._widgets[widget_id] = widget
        self._actions.append(self.addWidget(widget))

    def get_widget(self, widget_id):
        """Return a widget by unique id."""
        if widget_id in self._widgets:
            return self._widgets[widget_id]

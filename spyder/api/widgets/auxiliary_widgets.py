# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder API auxiliary widgets.
"""

# Third party imports
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QHBoxLayout, QMainWindow, QWidget
import qdarkstyle

# Local imports
from spyder.api.exceptions import SpyderAPIError
from spyder.config.gui import is_dark_interface


class SpyderWindowWidget(QMainWindow):
    """
    MainWindow subclass that contains a Spyder Plugin.
    """
    sig_closed = Signal()
    """
    This signal is emitted when this widget is closed.
    """

    # --- Signals
    # ------------------------------------------------------------------------
    sig_closed = Signal()
    """This signal is emitted when the close event is fired."""

    def __init__(self, widget):
        super().__init__()
        self.widget = widget

        # Setting interface theme
        if is_dark_interface():
            self.setStyleSheet(qdarkstyle.load_stylesheet())

    def closeEvent(self, event):
        """Override Qt method to emit a custom `sig_close` signal."""
        super().closeEvent(event)
        self.sig_closed.emit()


class MainCornerWidget(QWidget):
    """
    Corner widget to hold options menu, spinner and additional options.
    """

    def __init__(self, parent, name):
        super().__init__(parent)

        self._widgets = {}
        self.setObjectName(name)

        self._layout = QHBoxLayout()
        self.setLayout(self._layout)

        spacing = 2
        self._layout.setSpacing(2)

        # left, top, right, bottom
        self._layout.setContentsMargins(spacing, 0, spacing, spacing)
        self.setContentsMargins(0, 0, 0, 0)

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
        self._layout.insertWidget(0, widget)

    def get_widget(self, widget_id):
        """
        Return a widget by unique id..
        """
        if widget_id in self._widgets:
            return self._widgets[widget_id]

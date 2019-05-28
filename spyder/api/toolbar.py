# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
spyder.api.toolbar
==================

Toolbar widgets designed specifically for Spyder plugin widgets.
"""

# Third party imports
from qtpy.QtCore import QSize
from qtpy.QtWidgets import QApplication, QFrame, QHBoxLayout, QStyle, QWidget

# Local imports
from spyder.utils.qthelpers import set_iconsize_recursively


class SpyderPluginToolbar(QWidget):
    """
    Spyder plugin toolbar class.

    All plugin widgets must use this class for their uppermost toolbar.
    """

    def __init__(self, parent=None):
        super(SpyderPluginToolbar, self).__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.addStretch(1)
        self._stretch_index = 0

        style = QApplication.instance().style()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(style.pixelMetric(QStyle.PM_ToolBarItemSpacing))

    def add_widget(self, widget, ha='left'):
        """Add a widget to the toolbar."""
        if widget is None:
            widget = QFrame()
            widget.setFrameStyle(53)
        if ha == 'left':
            self.layout.insertWidget(self._stretch_index, widget)
            self._stretch_index += 1
        else:
            self.layout.addWidget(widget)

    def set_iconsize(self, iconsize):
        """Set the icon size of the toolbar."""
        set_iconsize_recursively(iconsize, self.layout)

    def add_options_button(self, options_button):
        """Add the options button to the toolbar."""
        if self.layout.itemAt(self.layout.count() - 1) is None:
            self.layout.insertWidget(self.layout.count() - 1, options_button)
        else:
            self.layout.addWidget(options_button)

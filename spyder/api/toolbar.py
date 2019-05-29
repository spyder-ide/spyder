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

        style = QApplication.instance().style()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(style.pixelMetric(QStyle.PM_ToolBarItemSpacing))

    def add_item(self, item, stretch=None):
        """
        Add a widget or a layout with a stretch factor stretch to the
        end of this toolbar.
        """
        if item is None:
            item = QFrame()
            item.setFrameStyle(53)
        if self.layout.itemAt(self.layout.count() - 1) is None:
            try:
                self.layout.insertWidget(self.layout.count() - 1, item)
            except TypeError:
                self.layout.insertLayout(self.layout.count() - 1, item)
        else:
            try:
                self.layout.addWidget(item)
            except TypeError:
                self.layout.addLayout(item)
        if stretch is not None:
            self.layout.setStretchFactor(item, stretch)

    def add_stretch(self, stretch):
        """
        Add a stretchable space with zero minimum size and stretch factor
        stretch to the end of this toolbar.
        """
        self.layout.addStretch(stretch)

    def add_spacing(self, spacing=None):
        """
        Add a non-stretchable space with size spacing to the end of
        this toolbar.
        """
        if spacing is None:
            style = QApplication.instance().style()
            spacing = style.pixelMetric(QStyle.PM_LayoutHorizontalSpacing)
        self.layout.addSpacing(spacing)

    def set_iconsize(self, iconsize):
        """Set the icon size of the toolbar."""
        set_iconsize_recursively(iconsize, self.layout)

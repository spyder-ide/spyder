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
from qtpy.QtWidgets import (QApplication, QFrame, QHBoxLayout, QStyle,
                            QWidget, QGridLayout, QVBoxLayout)

# Local imports
from spyder.utils.qthelpers import set_iconsize_recursively


class SpyderPluginToolbar(QWidget):
    """
    Spyder plugin toolbar class.

    All plugin widgets must use this class for their uppermost toolbar.
    """
    CLOSE_COL = 0
    CONTENT_COL = 2
    OPTIONS_COL = 4

    def __init__(self, parent=None):
        super(SpyderPluginToolbar, self).__init__(parent)
        self.layout = QGridLayout(self)
        self.layout.setHorizontalSpacing(0)

        bottom_margin = QApplication.instance().style().pixelMetric(
            QStyle.PM_ToolBarItemMargin)
        self.layout.setContentsMargins(0, 0, 0, bottom_margin)

    def _add_hboxlayout_at_row(self, row):
        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(QApplication.instance().style().pixelMetric(
            QStyle.PM_ToolBarItemSpacing))
        colspan = 1 if row == 0 else 3
        self.layout.addLayout(row_layout, row, self.CONTENT_COL, 1, colspan)

    def _get_hboxlayout_at_row(self, row):
        if self.layout.itemAtPosition(row, self.CONTENT_COL) is None:
            self._add_hboxlayout_at_row(row)
        return self.layout.itemAtPosition(row, self.CONTENT_COL)

    def set_row_visible(self, row, state):
        hboxlayout = self.layout.itemAtPosition(row, self.CONTENT_COL)
        if (state and not self.isVisible()) or hboxlayout is None:
            return
        for index in range(hboxlayout.count()):
            try:
                hboxlayout.itemAt(index).widget().setVisible(state)
            except AttributeError:
                pass

    def add_item(self, item, stretch=None, row=0):
        """
        Add a widget or a layout with an horizontal stretch factor stretch
        to the end of row row of this toolbar.
        """
        row_layout = self._get_hboxlayout_at_row(row)

        if item is None:
            item = QFrame()
            item.setFrameShape(QFrame.VLine)
            item.setFrameShadow(QFrame.Sunken)
        elif isinstance(item, int):
            self.add_spacing(spacing=item, row=row)

        column = row_layout.count()
        if row_layout.itemAt(column - 1) is None:
            column = max(0, column - 1)

        try:
            row_layout.insertWidget(column, item)
        except TypeError:
            row_layout.insertLayout(column, item)

        if stretch is not None:
            row_layout.setStretchFactor(item, stretch)

    def add_widget(self, widget, stretch=None, row=0):
        self.add_item(widget, stretch=stretch, row=row)

    def add_stretch(self, stretch, row=0):
        """
        Add a stretchable space with zero minimum size and stretch factor
        stretch to the end of this toolbar.
        """
        row_layout = self._get_hboxlayout_at_row(row)
        row_layout.addStretch(stretch)

    def add_spacing(self, spacing=None, row=0):
        """
        Add a non-stretchable space with size spacing to the end of
        this toolbar.
        """
        row_layout = self._get_hboxlayout_at_row(row)
        if spacing is None:
            spacing = QApplication.instance().style().pixelMetric(
                QStyle.PM_LayoutHorizontalSpacing)
        elif spacing == 'label':
            spacing = QApplication.instance().style().pixelMetric(
                QStyle.PM_CheckBoxLabelSpacing)
        row_layout.addSpacing(spacing)

    def add_options_btn(self, options_btn, spacing=None, stretch=1):
        if spacing is None:
            spacing = QApplication.instance().style().pixelMetric(
                QStyle.PM_ToolBarItemSpacing)
        self.layout.setColumnMinimumWidth(self.OPTIONS_COL - 1, spacing)
        if stretch is not None:
            self.layout.setColumnStretch(self.OPTIONS_COL - 1, stretch)
        self.layout.addWidget(options_btn, 0, self.OPTIONS_COL)

    def set_iconsize(self, iconsize):
        """Set the icon size of the toolbar."""
        set_iconsize_recursively(iconsize, self.layout)

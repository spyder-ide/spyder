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
                            QWidget, QGridLayout, QToolBar, QSizePolicy)

# Local imports
from spyder.utils.qthelpers import set_iconsize_recursively
from spyder.config.gui import get_toolbar_item_spacing


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
        self.layout.setContentsMargins(0, 0, 0, 0)

    def _add_hboxlayout_at_row(self, row):
        """Add a new QHBoxLayout at row."""
        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(get_toolbar_item_spacing())
        colspan = 1 if row == 0 else 3
        self.layout.addLayout(row_layout, row, self.CONTENT_COL, 1, colspan)

    def _get_hboxlayout_at_row(self, row):
        """
        Return the QHBoxLayout at row. Add one if it doesn't already exist.
        """
        if self.layout.itemAtPosition(row, self.CONTENT_COL) is None:
            self._add_hboxlayout_at_row(row)
        return self.layout.itemAtPosition(row, self.CONTENT_COL)

    def set_row_visible(self, row, state):
        """
        Set the visibility of all widgets at row to state.
        """
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
        Add a widget, a separator or an empty space to the end of this
        toolbar's row.
        """
        if item is None:
            self.add_separator(row)
        elif isinstance(item, int):
            self.add_spacing(spacing=item, row=row)
        else:
            self.add_widget(item, stretch, row)

    def add_separator(self, row=0):
        """
        Add a separator to the end of this toolbar's row.
        """
        separator = QToolBar()
        separator.addSeparator()
        separator.setStyleSheet(
            "QToolBar {border: 0px; background: transparent}")
        policy = separator.sizePolicy()
        policy.setVerticalPolicy(QSizePolicy.Expanding)
        separator.setSizePolicy(policy)
        self.add_widget(separator, stretch=None, row=row)

    def add_widget(self, widget, stretch=None, row=0):
        """
        Add a widget with an horizontal stretch factor stretch to the end
        of this toolbar's row.
        """
        row_layout = self._get_hboxlayout_at_row(row)
        row_layout.addWidget(widget)
        if stretch is not None:
            row_layout.setStretchFactor(widget, stretch)

    def add_stretch(self, stretch, row=0):
        """
        Add a stretchable space with zero minimum size and stretch factor
        stretch to the end of this toolbar's row.
        """
        row_layout = self._get_hboxlayout_at_row(row)
        row_layout.addStretch(stretch)

    def add_spacing(self, spacing=None, row=0):
        """
        Add a non-stretchable space with size spacing to the end
        of this toolbar's row.
        """
        row_layout = self._get_hboxlayout_at_row(row)
        if spacing is None:
            spacing = QApplication.instance().style().pixelMetric(
                QStyle.PM_LayoutHorizontalSpacing)
        elif spacing == 'label':
            spacing = QApplication.instance().style().pixelMetric(
                QStyle.PM_CheckBoxLabelSpacing)
        row_layout.addSpacing(spacing)

    def add_options_button(self, options_button, stretch=1):
        """Add `options_button` to the top right corner of this toolbar."""
        self.layout.setColumnMinimumWidth(
            self.OPTIONS_COL - 1, get_toolbar_item_spacing())
        if stretch is not None:
            self.layout.setColumnStretch(self.OPTIONS_COL - 1, stretch)
        self.layout.addWidget(options_button, 0, self.OPTIONS_COL)

    def add_close_button(self, close_button):
        """Add `close_button` to the top left corner of this toolbar."""
        spacing = QApplication.instance().style().pixelMetric(
            QStyle.PM_LayoutHorizontalSpacing)
        self.layout.setColumnMinimumWidth(self.CLOSE_COL + 1, spacing)
        self.layout.addWidget(close_button, 0, self.CLOSE_COL)

    def set_iconsize(self, iconsize):
        """Set the icon size of the toolbar."""
        set_iconsize_recursively(iconsize, self.layout)

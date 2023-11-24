# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder Combobox widget.

Use this for any combobox you want to add to Spyder.
"""

import qstylizer.style
from qtpy.QtCore import QSize, Qt
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QComboBox, QStyledItemDelegate

from spyder.utils.palette import QStylePalette
from spyder.utils.stylesheet import AppStyle


class _SpyderComboBoxDelegate(QStyledItemDelegate):
    """
    Delegate to make separators color follow our theme.

    Adapted from https://stackoverflow.com/a/33464045/438386
    """

    def paint(self, painter, option, index):
        data = index.data(Qt.AccessibleDescriptionRole)
        if data and data == "separator":
            painter.setPen(QColor(QStylePalette.COLOR_BACKGROUND_6))
            painter.drawLine(
                option.rect.left() + AppStyle.MarginSize,
                option.rect.center().y(),
                option.rect.right() - AppStyle.MarginSize,
                option.rect.center().y()
            )
        else:
            super().paint(painter, option, index)

    def sizeHint(self, option, index):
        data = index.data(Qt.AccessibleDescriptionRole)
        if data and data == "separator":
            return QSize(0, 3 * AppStyle.MarginSize)

        return super().sizeHint(option, index)


class SpyderComboBox(QComboBox):
    """Combobox widget for Spyder when its items don't have icons."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # This is also necessary to have more fine-grained control over the
        # style of our comboboxes with css, e.g. to add more padding between
        # its items.
        # See https://stackoverflow.com/a/33464045/438386 for the details.
        self.setItemDelegate(_SpyderComboBoxDelegate(self))

        self._css = self._generate_stylesheet()
        self.setStyleSheet(self._css.toString())

    def contextMenuEvent(self, event):
        # Prevent showing context menu for editable comboboxes because it's
        # added automatically by Qt. That means that the menu is not built
        # using our API and it's not localized.
        pass

    def _generate_stylesheet(self):
        css = qstylizer.style.StyleSheet()

        # Make our comboboxes have a uniform height
        css.QComboBox.setValues(
            minHeight=f'{AppStyle.ComboBoxMinHeight}em'
        )

        # Add top and bottom padding to the inner contents of comboboxes
        css["QComboBox QAbstractItemView"].setValues(
            paddingTop=f"{2 * AppStyle.MarginSize}px",
            paddingBottom=f"{2 * AppStyle.MarginSize}px"
        )

        # Add margin and padding to combobox items
        css["QComboBox QAbstractItemView::item"].setValues(
            marginLeft=f"{AppStyle.MarginSize}px",
            marginRight=f"{AppStyle.MarginSize}px",
            padding=f"{AppStyle.MarginSize}px"
        )

        # Make color of hovered combobox items match the one used in other
        # Spyder widgets
        css["QComboBox QAbstractItemView::item:selected:active"].setValues(
            backgroundColor=QStylePalette.COLOR_BACKGROUND_3,
        )

        return css


class SpyderComboBoxWithIcons(SpyderComboBox):
    """"Combobox widget for Spyder when its items have icons."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Padding is not necessary because icons give items enough of it.
        self._css["QComboBox QAbstractItemView::item"].setValues(
            padding="0px"
        )

        self.setStyleSheet(self._css.toString())

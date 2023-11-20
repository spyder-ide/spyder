# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder Combobox widget.

Use this for any combobox you want to add to Spyder.
"""

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
    """ComboBox widget to be used anywhere in Spyder."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # This is also necessary to have more fine-grained control over the
        # style of our comboboxes with css, e.g. to add more padding between
        # its items.
        # See https://stackoverflow.com/a/33464045/438386 for the details.
        self.setItemDelegate(_SpyderComboBoxDelegate(self))

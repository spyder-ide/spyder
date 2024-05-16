# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder combobox widgets.

Use these widgets for any combobox you want to add to Spyder.
"""

# Standard library imports
import sys

# Third-party imports
import qstylizer.style
from qtpy import PYQT5, PYQT6
from qtpy.QtCore import QSize, Qt, Signal
from qtpy.QtGui import QColor
from qtpy.QtWidgets import (
    QComboBox,
    QFontComboBox,
    QFrame,
    QLineEdit,
    QProxyStyle,
    QStyle,
    QStyledItemDelegate
)

# Local imports
from spyder.utils.palette import SpyderPalette
from spyder.utils.stylesheet import AppStyle, WIN


class _SpyderComboBoxProxyStyle(QProxyStyle):
    """Style proxy to adjust qdarkstyle issues."""

    def styleHint(self, hint, option=None, widget=None, returnData=None):
        if hint == QStyle.SH_ComboBox_Popup:
            # Disable combobox popup top & bottom areas.
            # See spyder-ide/spyder#9682.
            # Taken from https://stackoverflow.com/a/21019371
            return 0

        return QProxyStyle.styleHint(self, hint, option, widget, returnData)


class _SpyderComboBoxDelegate(QStyledItemDelegate):
    """
    Delegate to make separators color follow our theme.

    Adapted from https://stackoverflow.com/a/33464045/438386
    """

    def paint(self, painter, option, index):
        data = index.data(Qt.AccessibleDescriptionRole)
        if data and data == "separator":
            painter.setPen(QColor(SpyderPalette.COLOR_BACKGROUND_6))
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


class _SpyderComboBoxLineEdit(QLineEdit):
    """Dummy lineedit used for non-editable comboboxes."""

    sig_mouse_clicked = Signal()

    def __init__(self, parent):
        super().__init__(parent)

        # Fix style issues
        css = qstylizer.style.StyleSheet()
        css.QLineEdit.setValues(
            # These are necessary on Windows to prevent some ugly visual
            # glitches.
            backgroundColor="transparent",
            border="none",
            padding="0px",
            # Make text look centered for short comboboxes
            paddingRight=f"-{3 if WIN else 2}px"
        )

        self.setStyleSheet(css.toString())

    def mouseReleaseEvent(self, event):
        self.sig_mouse_clicked.emit()
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        # Avoid selecting the lineedit text with double clicks
        pass


class _SpyderComboBoxMixin:
    """Mixin with the basic style and functionality for our comboboxes."""

    def __init__(self):

        # Style
        self._css = self._generate_stylesheet()
        self.setStyleSheet(self._css.toString())

        style = _SpyderComboBoxProxyStyle(None)
        style.setParent(self)
        self.setStyle(style)

    def contextMenuEvent(self, event):
        # Prevent showing context menu for editable comboboxes because it's
        # added automatically by Qt. That means the menu is not built using our
        # API and it's not localized.
        pass

    def _generate_stylesheet(self):
        """Base stylesheet for Spyder comboboxes."""
        css = qstylizer.style.StyleSheet()

        # Make our comboboxes have a uniform height
        css.QComboBox.setValues(
            minHeight=f'{AppStyle.ComboBoxMinHeight}em'
        )

        # Add top and bottom padding to the inner contents of comboboxes
        css["QComboBox QAbstractItemView"].setValues(
            paddingTop=f"{AppStyle.MarginSize + 1}px",
            paddingBottom=f"{AppStyle.MarginSize + 1}px"
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
            backgroundColor=SpyderPalette.COLOR_BACKGROUND_3,
        )

        return css


class SpyderComboBox(QComboBox, _SpyderComboBoxMixin):
    """Combobox widget for Spyder when its items don't have icons."""

    def __init__(self, parent=None):
        if PYQT5 or PYQT6:
            super().__init__(parent)
        else:
            QComboBox.__init__(self, parent)
            _SpyderComboBoxMixin.__init__(self)

        self.is_editable = None
        self._is_shown = False
        self._is_popup_shown = False

        # This is also necessary to have more fine-grained control over the
        # style of our comboboxes with css, e.g. to add more padding between
        # its items.
        # See https://stackoverflow.com/a/33464045/438386 for the details.
        self.setItemDelegate(_SpyderComboBoxDelegate(self))

    def showEvent(self, event):
        """Adjustments when the widget is shown."""

        if not self._is_shown:
            if not self.isEditable():
                self.is_editable = False
                self.setLineEdit(_SpyderComboBoxLineEdit(self))

                # This is necessary to make Qt position the popup widget below
                # the combobox for non-editable ones.
                # Solution from https://stackoverflow.com/a/45191141/438386
                self.setEditable(True)
                self.lineEdit().setReadOnly(True)

                # Show popup when the lineEdit is clicked, which is the default
                # behavior for non-editable comboboxes in Qt.
                self.lineEdit().sig_mouse_clicked.connect(self.showPopup)
            else:
                self.is_editable = True

            self._is_shown = True

        super().showEvent(event)

    def showPopup(self):
        """Adjustments when the popup is shown."""
        super().showPopup()

        if sys.platform == "darwin":
            # Reposition popup to display it in the right place.
            # Solution from https://forum.qt.io/post/349517
            popup = self.findChild(QFrame)
            popup.move(popup.x() - 3, popup.y() + 4)

            # Adjust width to match the lineEdit one.
            if not self._is_popup_shown:
                popup.setFixedWidth(popup.width() + 2)
                self._is_popup_shown = True
        else:
            # Make borders straight to make popup feel as part of the combobox.
            # This doesn't work reliably on Mac.
            self._css.QComboBox.setValues(
                borderBottomLeftRadius="0px",
                borderBottomRightRadius="0px",
            )

            self.setStyleSheet(self._css.toString())

    def hidePopup(self):
        """Adjustments when the popup is hidden."""
        super().hidePopup()

        if not sys.platform == "darwin":
            # Make borders rounded when popup is not visible. This doesn't work
            # reliably on Mac.
            self._css.QComboBox.setValues(
                borderBottomLeftRadius=SpyderPalette.SIZE_BORDER_RADIUS,
                borderBottomRightRadius=SpyderPalette.SIZE_BORDER_RADIUS,
            )

            self.setStyleSheet(self._css.toString())


class SpyderComboBoxWithIcons(SpyderComboBox):
    """"Combobox widget for Spyder when its items have icons."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Padding is not necessary because icons give items enough of it.
        self._css["QComboBox QAbstractItemView::item"].setValues(
            padding="0px"
        )

        self.setStyleSheet(self._css.toString())


class SpyderFontComboBox(QFontComboBox, _SpyderComboBoxMixin):

    def __init__(self, parent=None):
        super().__init__(parent)

        # This is necessary for items to get the style set in our stylesheet.
        self.setItemDelegate(QStyledItemDelegate(self))

        # Adjust popup width to contents.
        self.setSizeAdjustPolicy(
            QComboBox.AdjustToMinimumContentsLengthWithIcon
        )

    def showPopup(self):
        """Adjustments when the popup is shown."""
        super().showPopup()

        if sys.platform == "darwin":
            popup = self.findChild(QFrame)
            popup.move(popup.x() - 3, popup.y() + 4)
